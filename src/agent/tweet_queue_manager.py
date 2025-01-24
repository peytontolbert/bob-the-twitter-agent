import json
import os
import asyncio
from typing import Optional, List, Dict
from datetime import datetime
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)

class TweetQueueManager:
    def __init__(self, queue_file: str = "tweets_queue.json", tweets_dir: str = "pending_tweets"):
        self.queue_file = queue_file
        self.tweets_dir = tweets_dir
        self.observer = None
        self._initialize_directories()
        self._setup_file_watcher()
        
    def _initialize_directories(self):
        """Initialize the queue file and tweets directory"""
        if not os.path.exists(self.tweets_dir):
            os.makedirs(self.tweets_dir)
        if not os.path.exists(self.queue_file):
            self._save_queue([])
    
    def _setup_file_watcher(self):
        """Setup watchdog observer for the tweets directory"""
        self.observer = Observer()
        self.observer.schedule(
            TweetFileWatcher(self),
            self.tweets_dir,
            recursive=False
        )
        self.observer.start()
    
    def _save_queue(self, tweets: List[Dict]):
        """Save tweets to queue file"""
        with open(self.queue_file, 'w') as f:
            json.dump({
                "updated_at": datetime.now().isoformat(),
                "tweets": tweets
            }, f, indent=2)
    
    def _load_queue(self) -> List[Dict]:
        """Load tweets from queue file"""
        try:
            with open(self.queue_file, 'r') as f:
                data = json.load(f)
                return data.get("tweets", [])
        except Exception as e:
            logger.error(f"Error loading tweet queue: {e}")
            return []
    
    def process_new_tweet_file(self, file_path: str) -> bool:
        """Process a new tweet file and add it to the queue"""
        try:
            # Read tweet content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # Get metadata if present (from first line comments)
            metadata = {}
            lines = content.split('\n')
            while lines and lines[0].startswith('#'):
                meta_line = lines.pop(0)[1:].strip()
                if ':' in meta_line:
                    key, value = meta_line.split(':', 1)
                    metadata[key.strip()] = value.strip()
            
            content = '\n'.join(lines).strip()
            
            # Add to queue
            success = self.add_tweet(content, metadata)
            
            # Move processed file to backup
            if success:
                backup_dir = os.path.join(self.tweets_dir, "processed")
                os.makedirs(backup_dir, exist_ok=True)
                backup_path = os.path.join(
                    backup_dir,
                    f"tweet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                )
                os.rename(file_path, backup_path)
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing tweet file {file_path}: {e}")
            return False
    
    def add_tweet(self, content: str, metadata: Dict = None) -> bool:
        """Add a tweet to the queue"""
        try:
            tweets = self._load_queue()
            
            # Add new tweet
            tweets.append({
                "content": content,
                "added_at": datetime.now().isoformat(),
                "status": "pending",
                "metadata": metadata or {}
            })
            
            self._save_queue(tweets)
            return True
            
        except Exception as e:
            logger.error(f"Error adding tweet to queue: {e}")
            return False
    
    def get_next_tweet(self) -> Optional[Dict]:
        """Get next pending tweet from queue"""
        tweets = self._load_queue()
        pending_tweets = [t for t in tweets if t["status"] == "pending"]
        return pending_tweets[0] if pending_tweets else None
    
    def mark_tweet_posted(self, tweet_content: str):
        """Mark a tweet as posted and remove it from queue"""
        tweets = self._load_queue()
        tweets = [t for t in tweets if t["content"] != tweet_content]
        self._save_queue(tweets)
    
    def cleanup(self):
        """Clean up resources"""
        if self.observer:
            self.observer.stop()
            self.observer.join()


class TweetFileWatcher(FileSystemEventHandler):
    def __init__(self, queue_manager: TweetQueueManager):
        self.queue_manager = queue_manager
    
    def on_created(self, event):
        if event.is_directory:
            return
            
        if event.src_path.endswith('.txt'):
            logger.info(f"New tweet file detected: {event.src_path}")
            # Small delay to ensure file is completely written
            asyncio.create_task(self._process_after_delay(event.src_path))
    
    async def _process_after_delay(self, file_path: str):
        await asyncio.sleep(1)  # Wait for file to be completely written
        self.queue_manager.process_new_tweet_file(file_path) 