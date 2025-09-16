import pandas as pd
import json
import os
import glob

def process_json_files():
    # Get all JSON files in the current directory
    json_files = [f for f in glob.glob("*.json") if f != "processed_urls.json"]
    
    # Dictionary to store DataFrames with conversation_id as key
    all_dataframes = {}
    failed_files = []
    
    print(f"Found {len(json_files)} JSON files to process")
    
    for json_file in json_files:
        try:
            print(f"\nProcessing: {json_file}")
            
            # Read JSON file
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract required information
            # If channel_name is missing, try to extract from URL
            if 'channel_name' not in data and 'url' in data:
                url_parts = data['url'].split('/')
                for i, part in enumerate(url_parts):
                    if part in ['x.com', 'twitter.com'] and i + 1 < len(url_parts):
                        data['channel_name'] = url_parts[i + 1]
                        break
            
            channel_name = data.get('channel_name', 'unknown')
            url = data.get('url', '')
            conversation_id = data.get('conversation_id', '')
            comments = data.get('comments', [])
            
            if not conversation_id or not comments:
                print(f"Missing required data in {json_file}")
                failed_files.append(json_file)
                continue
            
            # Create DataFrame from comments
            df = pd.DataFrame(comments)
            
            if df.empty:
                print(f"No comments found in {json_file}")
                failed_files.append(json_file)
                continue
            
            # Create channel_name and url columns with NaN values
            df['channel_name'] = pd.NA
            df['url'] = pd.NA
            
            # Set channel_name and url only for the first row
            df.loc[0, 'channel_name'] = channel_name
            df.loc[0, 'url'] = url
            
            # Ensure required columns exist
            if 'text' not in df.columns or 'timestamp' not in df.columns:
                print(f"Missing required columns in {json_file}")
                failed_files.append(json_file)
                continue
            
            # Reorder columns to match required format
            df = df[['channel_name', 'url', 'text', 'timestamp']]
            
            # Rename columns
            df = df.rename(columns={'text': 'comments'})
            
            # Store DataFrame in dictionary
            all_dataframes[conversation_id] = df
            
            print(f"Successfully processed {len(comments)} comments from {channel_name}")
            print(f"Conversation ID: {conversation_id}")
            
        except Exception as e:
            print(f"\nError processing {json_file}:")
            print(f"Error details: {str(e)}")
            failed_files.append(json_file)
            continue
    
    # Print summary before saving
    print("\n=== Processing Summary ===")
    print(f"Total files found: {len(json_files)}")
    print(f"Successfully processed: {len(all_dataframes)}")
    print(f"Failed to process: {len(failed_files)}")
    
    if failed_files:
        print("\nFailed files:")
        for file in failed_files:
            print(f"- {file}")
    
    # Save all DataFrames to a single Excel file with multiple sheets
    if all_dataframes:
        output_file = 'twitter_comments.xlsx'
        print(f"\nSaving data to {output_file}...")
        
        try:
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                for conversation_id, df in all_dataframes.items():
                    # Truncate sheet name if too long (Excel has a 31 character limit)
                    sheet_name = conversation_id[:31]
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            print(f"Successfully saved data to {output_file}")
            print(f"Total sheets (conversation_ids) saved: {len(all_dataframes)}")
        except Exception as e:
            print(f"Error saving to Excel: {str(e)}")
    else:
        print("No data to save")

if __name__ == "__main__":
    process_json_files()
