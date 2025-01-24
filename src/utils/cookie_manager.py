import os
import json
import pickle
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class CookieManager:
    def __init__(self, domain: str = "x.com"):
        self.domain = domain
        self.base_dir = Path("cookies")
        self.cookie_file = self.base_dir / f"{domain}_cookies.pkl"
        self.storage_file = self.base_dir / f"{domain}_local_storage.json"
        self._ensure_directories()
        
    def _ensure_directories(self):
        """Ensure necessary directories exist"""
        self.base_dir.mkdir(exist_ok=True)
    
    def save_session(self, cookies: list, local_storage: dict):
        """Save session data with timestamp"""
        try:
            # Save cookies
            with open(self.cookie_file, 'wb') as f:
                pickle.dump({
                    'timestamp': datetime.now().isoformat(),
                    'cookies': cookies
                }, f)
            
            # Save local storage
            with open(self.storage_file, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'storage': local_storage
                }, f, indent=2)
                
            logger.info(f"Successfully saved session data for {self.domain}")
            
        except Exception as e:
            logger.error(f"Error saving session data: {e}")
    
    def load_session(self) -> tuple:
        """Load session data if not expired"""
        try:
            cookies = None
            local_storage = None
            
            # Load cookies if they exist and aren't expired
            if self.cookie_file.exists():
                with open(self.cookie_file, 'rb') as f:
                    data = pickle.load(f)
                    timestamp = datetime.fromisoformat(data['timestamp'])
                    if (datetime.now() - timestamp).days < 7:  # 7 day expiry
                        cookies = data['cookies']
            
            # Load local storage if it exists and isn't expired
            if self.storage_file.exists():
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                    timestamp = datetime.fromisoformat(data['timestamp'])
                    if (datetime.now() - timestamp).days < 7:  # 7 day expiry
                        local_storage = data['storage']
            
            return cookies, local_storage
            
        except Exception as e:
            logger.error(f"Error loading session data: {e}")
            return None, None
    
    def clear_session(self):
        """Clear saved session data"""
        try:
            if self.cookie_file.exists():
                self.cookie_file.unlink()
            if self.storage_file.exists():
                self.storage_file.unlink()
            logger.info(f"Successfully cleared session data for {self.domain}")
        except Exception as e:
            logger.error(f"Error clearing session data: {e}") 