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
    return f'new_data/{channel_name}_comments_{conversation_id}.json'

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
    comments = []
    seen_comments = set()
    last_height = 0
    consecutive_same_height = 0
    base_scroll_pause_time = 5
    scroll_pause_time = base_scroll_pause_time
    no_new_comments_count = 0
    request_count = 0

    print("Waiting for initial page load...")
    try:
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="tweetText"]'))
        )
        print("Page loaded successfully")
    except Exception as e:
        print("Warning: Timeout waiting for initial tweets to load")

    time.sleep(15)

    # --- Extract post data before comments ---
    post_data = {}
    try:
        post_element = driver.find_element(By.CSS_SELECTOR, '[data-testid="tweet"]')
        post_text = post_element.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]').text
        try:
            user_name = post_element.find_element(By.CSS_SELECTOR, 'div.r-1wbh5a2.r-dnmrzs span').text
        except Exception:
            user_name = None
        try:
            user_handle = post_element.find_element(By.CSS_SELECTOR, 'div.r-1wbh5a2.r-dnmrzs span+span').text
        except Exception:
            user_handle = None
        try:
            post_time = post_element.find_element(By.TAG_NAME, 'time').get_attribute('datetime')
        except Exception:
            post_time = None
        post_data = {
            'text': post_text,
            'user_name': user_name,
            'user_handle': user_handle,
            'post_time': post_time,
            'scrape_time': time.strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        print(f"Error extracting post details: {str(e)}")

    # --- Extract first page comments before scrolling ---
    print("Extracting first page comments before scrolling...")
    comment_elements = driver.find_elements(By.CSS_SELECTOR, '[data-testid="tweetText"]')
    for element in comment_elements:
        try:
            comment_text = element.text
            parent = element.find_element(By.XPATH, "./../../../../..")
            try:
                user_element = parent.find_element(By.CSS_SELECTOR, 'div.r-1wbh5a2.r-dnmrzs span')
                user_name = user_element.text
            except Exception:
                user_name = None
            try:
                time_element = parent.find_element(By.TAG_NAME, 'time')
                comment_time = time_element.get_attribute('datetime')
            except Exception:
                comment_time = None
            try:
                handle_element = parent.find_element(By.CSS_SELECTOR, 'div.r-1wbh5a2.r-dnmrzs span+span')
                user_handle = handle_element.text
            except Exception:
                user_handle = None
            comment_key = (comment_text, user_name, comment_time)
            if comment_text and comment_key not in seen_comments:
                seen_comments.add(comment_key)
                comments.append({
                    'text': comment_text,
                    'user_name': user_name,
                    'user_handle': user_handle,
                    'comment_time': comment_time,
                    'scrape_time': time.strftime('%Y-%m-%d %H:%M:%S')
                })
        except Exception as e:
            print(f"Error extracting comment details: {str(e)}")
            continue
    print(f"First page comments extracted: {len(comments)}")

    # --- Scrolling and extracting more comments ---
    print("Scrolling to load more comments...")
    last_height = driver.execute_script("return document.documentElement.scrollHeight")
    consecutive_same_height = 0
    for attempt in range(max_attempts):
        try:
            # Extract all comments before scrolling (allow duplicates)
            comment_elements = driver.find_elements(By.CSS_SELECTOR, '[data-testid="tweetText"]')
            for element in comment_elements:
                try:
                    comment_text = element.text
                    parent = element.find_element(By.XPATH, "./../../../../..")
                    try:
                        user_element = parent.find_element(By.CSS_SELECTOR, 'div.r-1wbh5a2.r-dnmrzs span')
                        user_name = user_element.text
                    except Exception:
                        user_name = None
                    try:
                        time_element = parent.find_element(By.TAG_NAME, 'time')
                        comment_time = time_element.get_attribute('datetime')
                    except Exception:
                        comment_time = None
                    try:
                        handle_element = parent.find_element(By.CSS_SELECTOR, 'div.r-1wbh5a2.r-dnmrzs span+span')
                        user_handle = handle_element.text
                    except Exception:
                        user_handle = None
                    comments.append({
                        'text': comment_text,
                        'user_name': user_name,
                        'user_handle': user_handle,
                        'comment_time': comment_time,
                        'scrape_time': time.strftime('%Y-%m-%d %H:%M:%S')
                    })
                except Exception as e:
                    print(f"Error extracting comment details: {str(e)}")
                    continue
            print(f"Comments collected before scroll: {len(comments)} (attempt {attempt+1})")
            save_comments_checkpoint(output_filename, comments, conversation_id, url, driver.execute_script("return document.documentElement.scrollHeight"))

            # Scroll to bottom
            driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(scroll_pause_time + 3)
            current_height = driver.execute_script("return document.documentElement.scrollHeight")
            if current_height == last_height:
                consecutive_same_height += 1
                print(f"No new scroll height detected (attempt {consecutive_same_height}/3)")
            else:
                consecutive_same_height = 0
            last_height = current_height

            # Click 'Show more replies' buttons if present
            try:
                show_more_buttons = driver.find_elements(By.XPATH, "//span[contains(text(), 'Show more replies')]")
                for button in show_more_buttons:
                    driver.execute_script("arguments[0].click();", button)
                    print("Clicked 'Show more replies' button.")
                    time.sleep(5)
            except Exception:
                pass

            # Click 'Show probable spam' buttons if present
            try:
                spam_buttons = driver.find_elements(By.XPATH, "//span[contains(text(), 'Show probable spam')]")
                for button in spam_buttons:
                    driver.execute_script("arguments[0].click();", button)
                    print("Clicked 'Show probable spam' button.")
                    time.sleep(5)
            except Exception:
                pass

            # Extract all comments after scrolling (allow duplicates)
            comment_elements = driver.find_elements(By.CSS_SELECTOR, '[data-testid="tweetText"]')
            for element in comment_elements:
                try:
                    comment_text = element.text
                    parent = element.find_element(By.XPATH, "./../../../../..")
                    try:
                        user_element = parent.find_element(By.CSS_SELECTOR, 'div.r-1wbh5a2.r-dnmrzs span')
                        user_name = user_element.text
                    except Exception:
                        user_name = None
                    try:
                        time_element = parent.find_element(By.TAG_NAME, 'time')
                        comment_time = time_element.get_attribute('datetime')
                    except Exception:
                        comment_time = None
                    try:
                        handle_element = parent.find_element(By.CSS_SELECTOR, 'div.r-1wbh5a2.r-dnmrzs span+span')
                        user_handle = handle_element.text
                    except Exception:
                        user_handle = None
                    comments.append({
                        'text': comment_text,
                        'user_name': user_name,
                        'user_handle': user_handle,
                        'comment_time': comment_time,
                        'scrape_time': time.strftime('%Y-%m-%d %H:%M:%S')
                    })
                except Exception as e:
                    print(f"Error extracting comment details: {str(e)}")
                    continue
            print(f"Comments collected after scroll: {len(comments)} (attempt {attempt+1})")
            save_comments_checkpoint(output_filename, comments, conversation_id, url, driver.execute_script("return document.documentElement.scrollHeight"))

            # Stop if no new comments after three consecutive scrolls with same height
            if consecutive_same_height >= 3:
                print("No new comments or scroll height after 3 attempts. Stopping.")
                break
        except Exception as e:
            print(f"Error during scrolling: {str(e)}")
            continue

    print(f"Total comments extracted: {len(comments)}")
    return {'post': post_data, 'comments': comments}

def login_to_twitter(driver, username, password):
    """Handle Twitter login"""
    driver.get("https://twitter.com/i/flow/login")
    time.sleep(10)

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
        username = "************"
        password = "***********"
        
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
                time.sleep(10)  # Increased wait for page load
                
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
                time.sleep(10)
                
            except Exception as e:
                print(f"Error processing URL {url}: {str(e)}")
                continue

    except Exception as e:
        print(f"An error occurred: {str(e)}")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
