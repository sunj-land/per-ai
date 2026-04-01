#!/bin/bash
# scripts/migrate-skills.sh

set -e

BACKUP_DIR="agents/skills.bak"
SOURCE_DIR="agents/skills"
TARGET_DIR="skills"

function rollback() {
    echo "Rolling back..."
    
    # Restore directory
    if [ -d "$TARGET_DIR" ]; then
        echo "Removing $TARGET_DIR..."
        rm -rf "$TARGET_DIR"
    fi
    if [ -d "$BACKUP_DIR" ]; then
        echo "Restoring $SOURCE_DIR from backup..."
        mv "$BACKUP_DIR" "$SOURCE_DIR"
    fi
    
    # Revert sed changes
    echo "Reverting imports in .py files..."
    # Exclude .venv and node_modules
    find . -name "*.py" -not -path "./.venv/*" -not -path "./node_modules/*" -print0 | xargs -0 sed -i '' 's/from skills/from agents.skills/g'
    find . -name "*.py" -not -path "./.venv/*" -not -path "./node_modules/*" -print0 | xargs -0 sed -i '' 's/import skills/import agents.skills/g'
    
    echo "Rollback complete."
}

if [ "$1" == "--rollback" ]; then
    rollback
    exit 0
fi

echo "Starting migration..."

# Check if source exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: Source directory $SOURCE_DIR not found!"
    # Check if already migrated
    if [ -d "$TARGET_DIR" ]; then
        echo "Target directory $TARGET_DIR already exists. Maybe migration was already run?"
    fi
    exit 1
fi

# Backup
echo "Backing up $SOURCE_DIR to $BACKUP_DIR..."
cp -r "$SOURCE_DIR" "$BACKUP_DIR"

# Move
echo "Moving $SOURCE_DIR to $TARGET_DIR..."
if [ -d "$TARGET_DIR" ]; then
    # If target exists, move contents
    mkdir -p "$TARGET_DIR"
    cp -R "$SOURCE_DIR/" "$TARGET_DIR/"
    rm -rf "$SOURCE_DIR"
else
    # If target doesn't exist, just rename
    mv "$SOURCE_DIR" "$TARGET_DIR"
fi

# Ensure __init__.py exists in new location
if [ ! -f "$TARGET_DIR/__init__.py" ]; then
    echo "Creating $TARGET_DIR/__init__.py..."
    touch "$TARGET_DIR/__init__.py"
fi

# Refactor imports
echo "Updating imports in .py files..."
# Using sed with empty extension for macOS compatibility
find . -name "*.py" -not -path "./.venv/*" -not -path "./node_modules/*" -print0 | xargs -0 sed -i '' 's/from agents.skills/from skills/g'
find . -name "*.py" -not -path "./.venv/*" -not -path "./node_modules/*" -print0 | xargs -0 sed -i '' 's/import agents.skills/import skills/g'

echo "Migration complete."
