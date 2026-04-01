import re
import httpx
import time
import os

API_URL = "http://localhost:8000/api/v1/feeds"
README_PATH = "temp_rss_repo/README.md"

def parse_readme():
    feeds = []
    if not os.path.exists(README_PATH):
        print(f"Error: {README_PATH} not found.")
        return feeds

    with open(README_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Regex to match table row: | Name | [Link](URL) | ...
    # Example: | 知乎每日精选 | [https://www.zhihu.com/rss](https://www.zhihu.com/rss) | ...
    pattern = re.compile(r'\|\s*(.*?)\s*\|\s*\[.*?\]\((.*?)\)\s*\|')

    for line in lines:
        line = line.strip()
        match = pattern.search(line)
        if match:
            name = match.group(1).strip()
            url = match.group(2).strip()
            
            # Basic validation
            if url.startswith('http'):
                feeds.append({"title": name, "url": url})
    
    return feeds

def add_feed(feed):
    try:
        payload = {
            "url": feed["url"],
            "title": feed["title"],
            "group_name": "Top RSS List"
        }
        response = httpx.post(API_URL, json=payload, timeout=10.0)
        if response.status_code == 200:
            print(f"Success: Added {feed['title']} ({feed['url']})")
            return True
        else:
            print(f"Failed: {feed['title']} ({feed['url']}) - Status: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Error adding {feed['title']}: {e}")
        return False

def main():
    print("Parsing README...")
    feeds = parse_readme()
    print(f"Found {len(feeds)} feeds.")

    success_count = 0
    for feed in feeds:
        if add_feed(feed):
            success_count += 1
        # Be nice to the server
        time.sleep(0.1)

    print(f"\nFinished. Successfully added {success_count}/{len(feeds)} feeds.")

if __name__ == "__main__":
    main()
