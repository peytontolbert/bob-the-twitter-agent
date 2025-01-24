import asyncio
import os
import sys
import logging
from pathlib import Path

# Suppress Selenium logging
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.agent.action_handler import ActionHandler

async def view_mentions():
    """View all mentions and their details"""
    handler = None
    try:
        handler = ActionHandler(headless=False)
        
        # Login
        print("Logging in...")
        is_logged_in = await handler.ensure_logged_in()
        if not is_logged_in:
            print("Failed to log in")
            return
        
        # Get mentions
        print("\nChecking mentions...")
        mentions = await handler.check_mentions()
        
        if not mentions:
            print("No mentions found")
            return
        
        print(f"\nFound {len(mentions)} mentions:")
        for i, mention in enumerate(mentions, 1):
            print(f"\nMention #{i}:")
            print("--------------------")
            print(f"From: {mention['username']}")
            print(f"Text: {mention['text']}")
            
            # Try to get tweet ID from status link
            links = mention['tweet_element'].find_elements("css selector", "a[href*='status']")
            for link in links:
                href = link.get_attribute('href')
                if href and 'status' in href:
                    try:
                        tweet_id = href.split('status/')[1].split('?')[0]
                        print(f"Tweet ID: {tweet_id}")
                    except:
                        pass
            print("--------------------")
        
    except Exception as e:
        print(f"Error viewing mentions: {e}")
    finally:
        if handler:
            try:
                handler.cleanup()
            except:
                pass  # Suppress any cleanup errors
        sys.exit(0)  # Exit cleanly

if __name__ == "__main__":
    asyncio.run(view_mentions()) 