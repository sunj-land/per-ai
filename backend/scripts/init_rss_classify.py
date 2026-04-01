import sys
import os
import logging
from pathlib import Path
from sqlmodel import Session, select

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add backend directory to sys.path
# Script is in backend/scripts/init_rss_classify.py
# Backend root is backend/
current_dir = Path(__file__).resolve().parent
backend_root = current_dir.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

try:
    from app.core.database import engine
    from app.services.rss_service import auto_classify_feeds
    from app.models.rss import RSSFeed, RSSGroup, RSSFeedGroupLink
except ImportError as e:
    logger.error(f"Failed to import app modules: {e}")
    sys.exit(1)

def main():
    logger.info("Starting RSS feed auto-classification initialization...")
    
    with Session(engine) as session:
        # Check current status
        total_feeds = session.exec(select(RSSFeed)).all()
        logger.info(f"Total feeds in database: {len(total_feeds)}")
        
        groups = session.exec(select(RSSGroup)).all()
        logger.info(f"Existing groups: {[g.name for g in groups]}")

        # Run classification
        try:
            result = auto_classify_feeds(session)
            logger.info(f"Auto-classification result: {result}")
        except Exception as e:
            logger.error(f"Error during auto-classification: {e}", exc_info=True)

if __name__ == "__main__":
    main()
