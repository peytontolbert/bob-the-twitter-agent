import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union
import logging

logger = logging.getLogger(__name__)

class ConversationMemory:
    def __init__(self):
        self.data_dir = Path("data/conversations")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.memory = {}
        self.load_all_conversations()
        
    def load_all_conversations(self):
        """Load all conversation files from disk"""
        try:
            for file in self.data_dir.glob("*.json"):
                handle = file.stem  # filename without extension
                with open(file, 'r', encoding='utf-8') as f:
                    self.memory[handle] = json.load(f)
                    logger.info(f"Loaded memory for {handle}")
        except Exception as e:
            logger.error(f"Error loading conversations: {e}")

    def save_conversation(self, handle: str):
        """Save a specific conversation to disk"""
        try:
            if handle in self.memory:
                file_path = self.data_dir / f"{handle}.json"
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.memory[handle], f, indent=2)
                logger.info(f"Saved memory for {handle}")
        except Exception as e:
            logger.error(f"Error saving conversation for {handle}: {e}")

    def save_all_conversations(self):
        """Save all conversations to disk"""
        for handle in self.memory:
            self.save_conversation(handle)

    def get_conversation(self, handle: str):
        """Get or create conversation memory for a handle"""
        if handle not in self.memory:
            self.memory[handle] = {
                'dms': [],
                'mentions': [],
                'last_interaction': None,
                'metadata': {
                    'first_seen': datetime.now().isoformat(),
                    'total_interactions': 0
                }
            }
        return self.memory[handle]

    def add_dm(self, handle: str, message: dict):
        """Add a DM to memory"""
        conv = self.get_conversation(handle)
        message['type'] = 'dm'
        conv['dms'].append(message)
        conv['last_interaction'] = datetime.now().isoformat()
        conv['metadata']['total_interactions'] += 1
        self.save_conversation(handle)

    def add_mention(self, handle: str, mention_data: dict):
        """Add a mention to the conversation memory"""
        try:
            # Get or create conversation for this handle
            conversation = self.get_conversation(handle)
            if not conversation:
                conversation = {
                    'handle': handle,
                    'dms': [],
                    'mentions': [],
                    'last_interaction': None,
                    'total_interactions': 0
                }
                
            # Add mention to mentions list
            mentions = conversation.get('mentions', [])
            mentions.append(mention_data)
            conversation['mentions'] = mentions
            
            # Update interaction metadata
            conversation['last_interaction'] = datetime.now().isoformat()
            conversation['total_interactions'] += 1
            
            # Save conversation data
            self.save_conversation(handle)
            
        except Exception as e:
            logger.error(f"Error adding mention: {e}")

    def get_recent_context(self, handle: str, limit: int = 5) -> List[Dict]:
        """Get recent conversation context for a handle"""
        try:
            messages = self.memory.get(handle, [])
            if not messages:
                return []
                
            # Sort by timestamp, handling None values
            def get_timestamp(msg):
                ts = msg.get('timestamp')
                if ts is None:
                    return ''  # Return empty string for None timestamps
                return str(ts)  # Convert all timestamps to strings for comparison
                
            messages.sort(key=get_timestamp)
            
            # Return most recent messages
            return messages[-limit:]
            
        except Exception as e:
            logger.error(f"Error getting context for {handle}: {e}")
            return []

    def get_dm_history(self, handle: str, limit: int = None):
        """Get DM history for a handle"""
        conv = self.get_conversation(handle)
        messages = conv['dms']
        return messages[-limit:] if limit else messages

    def get_mention_history(self, handle: str, limit: int = None):
        """Get mention history for a handle"""
        conv = self.get_conversation(handle)
        mentions = conv['mentions']
        return mentions[-limit:] if limit else mentions

    def get_all_handles(self):
        """Get list of all handles in memory"""
        return list(self.memory.keys())

    def get_metadata(self, handle: str):
        """Get metadata for a handle"""
        conv = self.get_conversation(handle)
        return conv['metadata']

    def update_metadata(self, handle: str, key: str, value):
        """Update metadata for a handle"""
        conv = self.get_conversation(handle)
        conv['metadata'][key] = value
        self.save_conversation(handle)

    def get_dms(self, handle: str, limit: Optional[int] = None) -> List[Dict]:
        """Get DMs for a handle, optionally limited to the most recent n messages"""
        if handle not in self.memory:
            return []
        dms = self.memory[handle]["dms"]
        if limit:
            return dms[-limit:]
        return dms

    def get_mentions(self, handle: str, limit: Optional[int] = None) -> List[Dict]:
        """Get mentions for a handle, optionally limited to the most recent n messages"""
        if handle not in self.memory:
            return []
        mentions = self.memory[handle]["mentions"]
        if limit:
            return mentions[-limit:]
        return mentions

    def get_all_conversations(self, handle: str) -> Dict[str, List[Dict]]:
        """Get all conversations (DMs and mentions) for a handle"""
        if handle not in self.memory:
            return {"dms": [], "mentions": []}
        return self.memory[handle]

    def clear_memory(self, handle: str = None):
        """Clear memory for a specific handle or all handles"""
        if handle:
            if handle in self.memory:
                self.memory[handle] = {"dms": [], "mentions": []}
                self.save_conversation(handle)
        else:
            self.memory = {}
            # Remove all json files
            for file in self.data_dir.glob("*.json"):
                file.unlink()

    def has_replied_to_mention(self, handle: str, tweet_id: str) -> bool:
        """Check if we've already replied to a specific mention"""
        try:
            # Get conversation data for this handle
            conversation = self.get_conversation(handle)
            if not conversation:
                return False
                
            # Check mentions for this tweet ID
            mentions = conversation.get('mentions', [])
            for mention in mentions:
                if mention.get('tweet_id') == tweet_id and mention.get('is_reply', False):
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Error checking replied mentions: {e}")
            return False 