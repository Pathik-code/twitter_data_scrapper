# Twitter/X Comments Scraper and Processor

This project consists of two main Python scripts that work together to scrape and process comments from Twitter/X posts. The scripts are designed to handle multiple URLs and provide robust error handling and checkpoint saves.

## Features

- Automated Twitter/X login
- Scrapes comments from multiple Twitter/X posts
- Handles rate limiting and spam warnings
- Checkpoint saving to resume interrupted scraping
- Progress tracking for processed URLs
- Comment deduplication
- Comprehensive error handling
- Data processing and Excel export

## Requirements

- Python 3.x
- Chrome Browser
- ChromeDriver (compatible with your Chrome version)
- Required Python packages:
  - selenium
  - pandas
  - openpyxl

## File Structure

- `twitter_scraper_new.py`: Main scraping script
- `process_comments_new.py`: Comment processing script
- `DataPaper.csv`: Input file containing Twitter/X URLs to scrape
- `chromedriver`: Chrome WebDriver executable
- Various JSON files: Scraped comments for each URL
- `twitter_comments.xlsx`: Final processed output file

## Setup

1. Install required Python packages:
   ```bash
   pip install selenium pandas openpyxl
   ```

2. Download ChromeDriver that matches your Chrome browser version and place it in the project directory.

3. Create a `DataPaper.csv` file with Twitter/X URLs (one URL per line).

## Usage

### 1. Scraping Comments

Run the scraper script:
```bash
python twitter_scraper_new.py
```

The script will:
- Prompt for Twitter/X login credentials
- Process each URL from DataPaper.csv
- Save comments in JSON files
- Track progress in processed_urls.json

### 2. Processing Comments

After scraping, run the processing script:
```bash
python process_comments_new.py
```

The script will:
- Process all JSON files in the directory
- Combine and organize the data
- Generate an Excel file with processed comments

## Output Files

- Individual JSON files for each processed URL (`channelname_comments_conversationid.json`)
- `processed_urls.json`: Tracks which URLs have been processed
- `twitter_comments.xlsx`: Final processed data in Excel format

## Error Handling

The scripts include robust error handling for:
- Network issues
- Rate limiting
- Spam warnings
- Page loading problems
- Scroll failures

## Checkpointing

The scraper implements checkpointing to:
- Save progress every 20 comments
- Resume from last position if interrupted
- Track processed URLs
- Maintain scroll position

## Notes

- The scraper respects Twitter/X's rate limits with dynamic delays
- Comments are deduplicated during scraping
- The processor handles multiple data formats and edge cases
- Progress and errors are logged to the console

## Limitations

- Requires manual login credentials
- Subject to Twitter/X's rate limiting and anti-bot measures
- May need adjustments based on Twitter/X UI changes
- Processing large numbers of comments may be time-consuming

## Best Practices

1. Run the scraper with stable internet connection
2. Monitor the process for any rate limiting issues
3. Back up JSON files before processing
4. Review the Excel output for data quality
