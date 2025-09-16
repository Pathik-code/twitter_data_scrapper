from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import os

# Path to your ChromeDriver executable
CHROMEDRIVER_PATH = '/home/pathik/Videos/DataScrapping/chromedriver'

def extract_url_info(url):
    """Extract channel name and conversation ID from URL"""
    parts = url.strip().split('/')
    conversation_id = parts[-1]
    channel_name = parts[-3]  # Gets the account name like 'the_hindu' or 'timesofindia'
    return channel_name, conversation_id

def get_output_filename(url):
    """Generate output filename based on channel name and conversation ID"""
    channel_name, conversation_id = extract_url_info(url)
    return f'{channel_name}_comments_{conversation_id}.json'

def load_existing_comments(filename):
    """Load existing comments from file if it exists"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('comments', []), data.get('metadata', {}).get('last_scroll_position', 0)
    except FileNotFoundError:
        return [], 0

def save_comments_checkpoint(filename, comments, conversation_id, url, last_height):
    """Save comments to file as a checkpoint"""
    channel_name = url.split('/')[3]  # Extract channel name from URL
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            'channel_name': channel_name,
            'conversation_id': conversation_id,
            'url': url,
            'total_comments': len(comments),
            'scrape_start_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'comments': comments,
            'metadata': {
                'last_scroll_position': last_height,
                'last_save_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'raw_comment_count': len(comments)
            }
        }, f, ensure_ascii=False, indent=2)

def handle_spam_warning(driver):
    """Handle Twitter's spam warning popup"""
    try:
        # Look for the spam warning button using multiple possible selectors
        spam_button_selectors = [
            "//span[contains(text(), 'Show probable spam')]",
            "//div[@role='button'][contains(., 'Show probable spam')]",
            "//div[contains(@class, 'r-button')][contains(., 'Show probable spam')]"
        ]
        
        for selector in spam_button_selectors:
            try:
                print(f"Looking for spam warning with selector: {selector}")
                button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                
                # Try JavaScript click first
                try:
                    driver.execute_script("arguments[0].click();", button)
                    print("Successfully clicked spam warning button using JavaScript")
                except:
                    # Fallback to regular click
                    button.click()
                    print("Successfully clicked spam warning button using regular click")
                
                # Wait for content to load after clicking
                time.sleep(10)
                return True
            except Exception as e:
                print(f"Selector {selector} failed: {str(e)}")
                continue
        return False
    except Exception as e:
        print(f"Error handling spam warning: {str(e)}")
        return False

def scroll_and_extract_comments(driver, conversation_id, url, output_filename, max_attempts=100):
    """Advanced scrolling and extraction with multiple techniques and checkpointing"""
    comments = []  # Start fresh, don't use existing comments to avoid duplicates
    seen_comments = set()  # To track unique comments
    last_height = 0
    consecutive_same_height = 0
    base_scroll_pause_time = 15  # Reduced base time
    scroll_pause_time = base_scroll_pause_time
    no_new_comments_count = 0
    request_count = 0
    
    print("Waiting for initial page load...")
    # Wait for the first tweet to be visible
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="tweetText"]'))
        )
        print("Page loaded successfully")
    except Exception as e:
        print("Warning: Timeout waiting for initial tweets to load")
    
    time.sleep(15)  # Additional wait to ensure full load
    
    for attempt in range(max_attempts):
        try:
            # Check for spam warning before scrolling
            if handle_spam_warning(driver):
                time.sleep(10)  # Wait after handling spam warning
            
            # Get current scroll height
            current_height = driver.execute_script("return document.documentElement.scrollHeight")
            
            # Dynamic sleep time based on request count
            request_count += 1
            print(f"\n--- Scroll Attempt {attempt + 1}/{max_attempts} ---")
            print(f"Current comments collected: {len(comments)}")
            print(f"Current scroll height: {current_height}")
            print(f"Request count: {request_count}")
            
            if request_count % 10 == 0:
                scroll_pause_time = min(base_scroll_pause_time * 2, 90)
                print(f"Increasing pause time to {scroll_pause_time} seconds (10 requests milestone)")
            elif request_count % 20 == 0:
                print("Taking a longer break to avoid rate limiting...")
                print("Pausing for 120 seconds...")
                time.sleep(120)  # 2-minute break every 20 requests
                scroll_pause_time = base_scroll_pause_time
                print(f"Resetting pause time to {base_scroll_pause_time} seconds")
            
            # First try normal scroll to bottom
            driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(scroll_pause_time)
            
            # If normal scroll didn't work, try alternative scrolling methods
            if current_height == last_height:
                # Try scrolling in smaller increments with random delays
                scroll_amount = 500 + (request_count % 300)  # Vary scroll amount
                driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                time.sleep(2 + (request_count % 5))  # Variable delay
                driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                time.sleep(7 + (request_count % 5))  # Variable delay
                
                # Try to click "Show more replies" buttons if they exist
                try:
                    show_more_buttons = driver.find_elements(By.XPATH, "//span[contains(text(), 'Show more replies')]")
                    for button in show_more_buttons:
                        driver.execute_script("arguments[0].click();", button)
                        time.sleep(15)
                except:
                    pass
                    
                consecutive_same_height += 1
                if consecutive_same_height >= 5:  # If stuck at same height for 5 attempts
                    print("Reached the bottom of comments")
                    break
            else:
                consecutive_same_height = 0

            # Find and extract comments
            comment_elements = driver.find_elements(By.CSS_SELECTOR, '[data-testid="tweetText"]')
            current_comments_count = len(comments)
            
            for element in comment_elements:
                try:
                    comment_text = element.text
                    if comment_text and comment_text not in seen_comments:
                        seen_comments.add(comment_text)
                        comments.append({
                            'text': comment_text,
                            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                        })
                except Exception as e:
                    print(f"Error extracting comment: {str(e)}")
                    continue
            
            # Check if we found any new comments
            if len(comments) == current_comments_count:
                no_new_comments_count += 1
                print(f"No new comments found in this scroll (attempt {no_new_comments_count}/3)")
                if no_new_comments_count >= 3:
                    print("\n=== Completion Status ===")
                    print(f"Total comments collected: {len(comments)}")
                    print(f"No new comments in last 3 scrolls")
                    print("Moving to next URL...")
                    break
            else:
                new_comments = len(comments) - current_comments_count
                print(f"Found {new_comments} new comments in this scroll")
                no_new_comments_count = 0
            
            # Save checkpoint every 20 comments
            if len(comments) % 20 == 0 and len(comments) > 0:
                save_comments_checkpoint(output_filename, comments, conversation_id, url, current_height)
                print("\n=== Checkpoint Saved ===")
                print(f"Total comments: {len(comments)}")
                print(f"Current scroll height: {current_height}")
                print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Update last height
            last_height = current_height
            
        except Exception as e:
            print("\n=== Error Occurred ===")
            print(f"Scroll attempt {attempt + 1} failed")
            print(f"Error message: {str(e)}")
            print(f"Comments collected so far: {len(comments)}")
            
            # Save current progress before retry
            if len(comments) > 0:
                save_comments_checkpoint(output_filename, comments, conversation_id, url, current_height)
                print("Saved progress checkpoint before retry")
            
            # Check for spam warning first
            if handle_spam_warning(driver):
                print("Recovered from error by handling spam warning")
                time.sleep(10)
                continue
            
            # If not spam warning, use exponential backoff
            retry_delay = min(scroll_pause_time * (2 ** (attempt % 4)), 180)  # Max 3 minutes
            print(f"Using exponential backoff: {retry_delay} seconds")
            print("Waiting before retry...")
            time.sleep(retry_delay)
            
            # Refresh page if multiple consecutive errors
            if attempt > 0 and attempt % 3 == 0:
                print("Multiple errors occurred, refreshing page...")
                driver.refresh()
                time.sleep(15)
            
            continue
    
    return comments

def login_to_twitter(driver, username, password):
    """Handle Twitter login"""
    driver.get("https://twitter.com/i/flow/login")
    time.sleep(15)

    # Enter username
    username_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'input[autocomplete="username"]'))
    )
    username_input.send_keys(username)
    username_input.send_keys(Keys.RETURN)
    time.sleep(10)

    # Enter password
    password_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="password"]'))
    )
    password_input.send_keys(password)
    password_input.send_keys(Keys.RETURN)
    time.sleep(10)  # Wait for login to complete

def main():
    # Initialize Chrome WebDriver
    options = webdriver.ChromeOptions()
    options.add_argument('--start-maximized')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--disable-blink-features=AutomationControlled')

    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)

    try:
        # Load URLs from CSV file and track progress
        processed_urls_file = 'processed_urls.json'
        processed_urls = set()
        
        # Load previously processed URLs if file exists
        if os.path.exists(processed_urls_file):
            with open(processed_urls_file, 'r') as f:
                processed_urls = set(json.load(f))
        
        # Read URLs from CSV
        urls = []
        with open('DataPaper.csv', 'r') as f:
            for line in f:
                url = line.strip()
                if url and ('x.com/' in url or 'twitter.com/' in url) and '/status/' in url:
                    # Normalize URL
                    if not url.startswith('https://'):
                        url = 'https://' + url.replace('http://', '')
                    url = url.replace('twitter.com/', 'x.com/')
                    if url not in processed_urls:
                        urls.append(url)
        
        print(f"Found {len(urls)} new URLs to process")
        
        # Login to Twitter first
        print("Please enter your Twitter credentials:")
        username = "*******"
        password = "*******"
        
        login_to_twitter(driver, username, password)
        print("Login successful!")
        
        # Process each URL
        for url in urls:
            try:
                print(f"\nProcessing URL: {url}")
                channel_name, conversation_id = extract_url_info(url)
                output_filename = get_output_filename(url)
                
                # Navigate to the URL
                print(f"Navigating to {url}")
                driver.get(url)
                time.sleep(30)  # Increased wait for page load
                
                # Extract comments for this URL
                print(f"Starting to extract comments from {channel_name}'s post {conversation_id}")
                comments = scroll_and_extract_comments(driver, conversation_id, url, output_filename)
                
                # Save final version
                save_comments_checkpoint(output_filename, comments, conversation_id, url, 
                                      driver.execute_script("return document.documentElement.scrollHeight"))
                
                # Mark URL as processed
                processed_urls.add(url)
                with open(processed_urls_file, 'w') as f:
                    json.dump(list(processed_urls), f)
                
                print(f"Successfully processed {url}, found {len(comments)} comments")
                print("Waiting 30 seconds before next URL...")
                time.sleep(30)
                
            except Exception as e:
                print(f"Error processing URL {url}: {str(e)}")
                continue

    except Exception as e:
        print(f"An error occurred: {str(e)}")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
