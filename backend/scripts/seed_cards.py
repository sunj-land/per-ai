import os
import sys
from sqlmodel import Session, select
from datetime import datetime

# Adjust path to include the backend directory so we can import app modules
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.append(backend_dir)

# Import models and database
from app.core.database import engine, create_db_and_tables
from app.models.card import Card, CardVersion, CardStatus

# Define standard cards
STANDARD_CARDS = [
    {
        "name": "ProductCard",
        "type": "custom",
        "description": "A card for displaying product details including image, price, rating and actions.",
        "file": "ProductCard.vue"
    },
    {
        "name": "NewsCard",
        "type": "custom",
        "description": "A card for news articles with thumbnail, source, date and summary.",
        "file": "NewsCard.vue"
    },
    {
        "name": "UserProfileCard",
        "type": "custom",
        "description": "A profile card showing user avatar, bio, stats and follow actions.",
        "file": "UserProfileCard.vue"
    },
    {
        "name": "StatCard",
        "type": "custom",
        "description": "A simple statistic card with value, trend indicator and footer info.",
        "file": "StatCard.vue"
    },
    {
        "name": "GuideCard",
        "type": "custom",
        "description": "A step-by-step guide card with navigation buttons.",
        "file": "GuideCard.vue"
    },
    {
        "name": "MediaCard",
        "type": "custom",
        "description": "A multimedia card supporting video, audio or image content.",
        "file": "MediaCard.vue"
    },
    {
        "name": "FormCard",
        "type": "form",
        "description": "A card with form inputs for data collection.",
        "file": "FormCard.vue"
    }
]

def get_file_content(filename):
    """
    Read content from the frontend source directory.
    """
    # Path relative to project root (assuming script runs from project root or backend dir)
    # We navigate up from backend/scripts/ to project root, then down to frontend
    project_root = os.path.dirname(backend_dir)
    file_path = os.path.join(project_root, "frontend/packages/web/src/components/cards", filename)
    
    if not os.path.exists(file_path):
        print(f"Warning: File not found: {file_path}")
        return ""
        
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def seed_cards():
    """
    Seed the database with standard cards.
    """
    print("Initializing database...")
    create_db_and_tables()
    
    with Session(engine) as session:
        for card_info in STANDARD_CARDS:
            # Check if card exists
            statement = select(Card).where(Card.name == card_info["name"])
            existing_card = session.exec(statement).first()
            
            if existing_card:
                print(f"Skipping existing card: {card_info['name']}")
                continue
                
            print(f"Creating card: {card_info['name']}")
            
            # Read code
            code = get_file_content(card_info["file"])
            if not code:
                print(f"Skipping due to missing file for {card_info['name']}")
                continue
            
            # Create Card
            new_card = Card(
                name=card_info["name"],
                type=card_info["type"],
                description=card_info["description"],
                status=CardStatus.PUBLISHED,
                version=1
            )
            session.add(new_card)
            session.commit()
            session.refresh(new_card)
            
            # Create Version
            new_version = CardVersion(
                card_id=new_card.id,
                version=1,
                code=code,
                changelog="Initial seed from standard library"
            )
            session.add(new_version)
            session.commit()
            
            print(f"Successfully created {card_info['name']} (ID: {new_card.id})")

if __name__ == "__main__":
    seed_cards()
