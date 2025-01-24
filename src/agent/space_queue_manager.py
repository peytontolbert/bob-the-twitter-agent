import json
import os
import asyncio
from typing import Optional, List, Dict
from datetime import datetime
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)

class SpaceQueueManager:
    def __init__(self, queue_file: str = "spaces_queue.json"):
        self.queue_file = queue_file
        self.current_spaces = []
        self.observer = None
        self._initialize_queue_file()
        
    def _initialize_queue_file(self):
        """Initialize the queue file if it doesn't exist"""
        if not os.path.exists(self.queue_file):
            self._save_queue([])
    
    def _save_queue(self, spaces: List[Dict]):
        """Save spaces to queue file"""
        with open(self.queue_file, 'w') as f:
            json.dump({
                "updated_at": datetime.now().isoformat(),
                "spaces": spaces
            }, f, indent=2)
    
    def _load_queue(self) -> List[Dict]:
        """Load spaces from queue file"""
        try:
            with open(self.queue_file, 'r') as f:
                data = json.load(f)
                return data.get("spaces", [])
        except Exception as e:
            logger.error(f"Error loading queue: {e}")
            return []
    
    def add_space(self, space_url: str, metadata: Dict = None) -> bool:
        """Add a space to the queue"""
        try:
            spaces = self._load_queue()
            
            # Check if space already exists
            if any(space["url"] == space_url for space in spaces):
                return False
            
            # Add new space
            spaces.append({
                "url": space_url,
                "added_at": datetime.now().isoformat(),
                "status": "pending",
                "metadata": metadata or {}
            })
            
            self._save_queue(spaces)
            return True
            
        except Exception as e:
            logger.error(f"Error adding space to queue: {e}")
            return False
    
    def get_next_space(self) -> Optional[Dict]:
        """Get next pending space from queue"""
        spaces = self._load_queue()
        pending_spaces = [s for s in spaces if s["status"] == "pending"]
        return pending_spaces[0] if pending_spaces else None
    
    def mark_space_joined(self, space_url: str):
        """Mark a space as joined"""
        spaces = self._load_queue()
        for space in spaces:
            if space["url"] == space_url:
                space["status"] = "joined"
                space["joined_at"] = datetime.now().isoformat()
        self._save_queue(spaces)
    
    def mark_space_completed(self, space_url: str):
        """Mark a space as completed"""
        spaces = self._load_queue()
        spaces = [s for s in spaces if s["url"] != space_url]
        self._save_queue(spaces)

class SpaceFileWatcher(FileSystemEventHandler):
    def __init__(self, queue_manager: SpaceQueueManager):
        self.queue_manager = queue_manager
    
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(self.queue_manager.queue_file):
            logger.info("Space queue file modified, processing changes...") 