import os
import json

input_folder = 'processed_json'

for filename in os.listdir(input_folder):
    if filename.endswith('.json'):
        input_path = os.path.join(input_folder, filename)
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        comments_data = data.get('comments', [])
        # If comments_data is a dict, get the 'comments' list inside it
        if isinstance(comments_data, dict):
            comments = comments_data.get('comments', [])
        else:
            comments = comments_data
        url = data.get('url', '')
        if isinstance(comments, list) and len(comments) == 0:
            print(url)