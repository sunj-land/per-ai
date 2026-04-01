import sys
import os

# Add the backend directory to sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from sqlmodel import Session, select, func
from app.core.database import engine
from app.models.rss import RSSFeed, RSSArticle

def check_status():
    with Session(engine) as session:
        feed_count = session.exec(select(func.count(RSSFeed.id))).one()
        article_count = session.exec(select(func.count(RSSArticle.id))).one()
        
        print(f"Total Feeds: {feed_count}")
        print(f"Total Articles: {article_count}")
        
        # Check feed statuses
        feeds = session.exec(select(RSSFeed)).all()
        status_counts = {}
        for feed in feeds:
            status = feed.last_fetch_status
            status_counts[status] = status_counts.get(status, 0) + 1
            
        print("Feed Statuses:")
        for status, count in status_counts.items():
            print(f"  {status}: {count}")

        # If there are articles, print the first few
        if article_count > 0:
            articles = session.exec(select(RSSArticle).limit(5)).all()
            print("\nSample Articles:")
            for article in articles:
                print(f"  - {article.title} (Feed ID: {article.feed_id})")

if __name__ == "__main__":
    check_status()
