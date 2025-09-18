import os
import json
import regex
from collections import defaultdict

def is_valid_comment(text):
    # Returns True if text contains at least one letter or number in any language
    return bool(regex.search(r'\p{L}|\p{N}', text))

def process_json_files():
    input_folder = 'new_data'
    output_folder = 'processed_json'
    all_data_file = os.path.join(output_folder, 'all_processed_data_by_conversation.json')
    os.makedirs(output_folder, exist_ok=True)

    all_data = {}

    for filename in os.listdir(input_folder):
        if filename.endswith('.json'):
            input_path = os.path.join(input_folder, filename)
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            channel_name = data.get('channel_name', '')
            conversation_id = data.get('conversation_id', '')
            url = data.get('url', '')
            scrape_start_time = data.get('scrape_start_time', '')
            post = data['comments'].get('post', {})
            comments = data['comments'].get('comments', [])

            # Remove duplicate comments using a set
            comment_set = set()
            unique_comments = []
            for c in comments:
                key = c.get('text', '').strip()
                if key not in comment_set:
                    comment_set.add(key)
                    unique_comments.append(c)

            # Remove comments with no characters or numbers
            valid_comments = []
            for c in unique_comments:
                if is_valid_comment(c.get('text', '')):
                    # Remove user_handle from each comment
                    c.pop('user_handle', None)
                    valid_comments.append(c)

            # Remove user_handle from post
            post.pop('user_handle', None)

            # Build output in requested format
            post_id = conversation_id
            post_obj = {
                'post_id': post_id,
                'text': post.get('text', ''),
                'user_name': post.get('user_name', ''),
                'post_time': post.get('post_time', '')
            }
            comments_list = []
            for idx, c in enumerate(valid_comments, 1):
                comments_list.append({
                    'comment_id': f'{conversation_id}_{idx}',
                    'text': c.get('text', ''),
                    'user_name': c.get('user_name', ''),
                    'comment_time': c.get('comment_time', '')
                })
            # Remove the first comment if present
            if comments_list:
                comments_list = comments_list[1:]
            output_data = {
                'channel_name': channel_name,
                'conversation_id': conversation_id,
                'url': url,
                'total_comments': len(comments_list),  # updated count after removing first comment
                'post': post_obj,
                'comments': comments_list
            }
            # Save processed file for each conversation_id
            output_path = os.path.join(output_folder, f'{conversation_id}.json')
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({conversation_id: output_data}, f, ensure_ascii=False, indent=2)
            # Add to all_data
            all_data[conversation_id] = output_data

    # Save all processed data in one file, separated by conversation_id
    with open(all_data_file, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    process_json_files()
