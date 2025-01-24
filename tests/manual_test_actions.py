import asyncio
import sys
import os
from pathlib import Path
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add src to Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.agent.action_handler import ActionHandler
from src.utils.logger import setup_logger

logger = setup_logger("manual_tests", "logs/manual_tests.log")

class ManualActionTester:
    def __init__(self):
        load_dotenv()
        self.handler = ActionHandler(headless=False)  # Non-headless for manual testing
        self.current_menu = "main"
        self.running = True
        
    async def run(self):
        """Main test loop"""
        try:
            # Ensure logged in first
            if not await self.handler.ensure_logged_in():
                logger.error("Failed to log in")
                return
                
            while self.running:
                await self.show_menu()
                choice = input("Enter your choice: ").strip()
                await self.handle_choice(choice)
                
        except Exception as e:
            logger.error(f"Error in test run: {e}")
        finally:
            self.handler.cleanup()
    
    async def show_menu(self):
        """Show the current menu"""
        menus = {
            "main": """
=== X Platform Manual Test Menu ===
1. Space Actions
2. Tweet Actions
3. DM Actions
4. Navigation Tests
5. Login/Session Tests
6. Run All Tests
0. Exit
            """,
            "spaces": """
=== Space Actions ===
1. Find Spaces by Keywords
2. Join Space by URL
3. Request to Speak
4. Send Message in Space
5. Leave Space
6. Test Space Queue
0. Back
            """,
            "tweets": """
=== Tweet Actions ===
1. Post Single Tweet
2. Add Tweet to Queue
3. Process Tweet Queue
4. Post Thread
0. Back
            """,
            "dms": """
=== DM Actions ===
1. Check New DMs
2. Send DM
3. Reply to DM
0. Back
            """
        }
        print("\n" + menus.get(self.current_menu, menus["main"]))
    
    async def handle_choice(self, choice: str):
        """Handle menu choices"""
        handlers = {
            "main": self.handle_main_menu,
            "spaces": self.handle_space_menu,
            "tweets": self.handle_tweet_menu,
            "dms": self.handle_dm_menu
        }
        await handlers.get(self.current_menu, self.handle_main_menu)(choice)
    
    async def handle_main_menu(self, choice: str):
        """Handle main menu choices"""
        if choice == "1":
            self.current_menu = "spaces"
        elif choice == "2":
            self.current_menu = "tweets"
        elif choice == "3":
            self.current_menu = "dms"
        elif choice == "4":
            await self.test_navigation()
        elif choice == "5":
            await self.test_login_session()
        elif choice == "6":
            await self.run_all_tests()
        elif choice == "0":
            self.running = False
    
    async def handle_space_menu(self, choice: str):
        """Handle space menu choices"""
        try:
            if choice == "1":
                keywords = input("Enter keywords (comma-separated): ").split(",")
                spaces = await self.handler.find_relevant_spaces(keywords)
                print("\nFound Spaces:")
                for i, space in enumerate(spaces, 1):
                    print(f"{i}. {space['title']} by {space['host']}")
                
            elif choice == "2":
                url = input("Enter space URL: ")
                success = await self.handler.join_space_by_url(url)
                print(f"Join {'successful' if success else 'failed'}")
                
            elif choice == "3":
                if self.handler.current_space:
                    success = await self.handler.request_to_speak()
                    print(f"Request {'sent' if success else 'failed'}")
                else:
                    print("Not currently in a space")
                    
            elif choice == "4":
                if self.handler.current_space:
                    message = input("Enter message: ")
                    success = await self.handler.speak_in_space(message)
                    print(f"Message {'sent' if success else 'failed'}")
                else:
                    print("Not currently in a space")
                    
            elif choice == "5":
                await self.handler.leave_space()
                
            elif choice == "6":
                await self.test_space_queue()
                
            elif choice == "0":
                self.current_menu = "main"
                
        except Exception as e:
            logger.error(f"Error in space menu: {e}")
    
    async def handle_tweet_menu(self, choice: str):
        """Handle tweet menu choices"""
        try:
            if choice == "1":
                content = input("Enter tweet content: ")
                success = await self.handler.post_tweet(content)
                print(f"Tweet {'posted' if success else 'failed'}")
                
            elif choice == "2":
                content = input("Enter tweet content: ")
                self.handler.tweet_queue.add_tweet(content)
                print("Tweet added to queue")
                
            elif choice == "3":
                print("Processing tweet queue...")
                await self.handler.process_tweet_queue()
                
            elif choice == "4":
                await self.test_thread_posting()
                
            elif choice == "0":
                self.current_menu = "main"
                
        except Exception as e:
            logger.error(f"Error in tweet menu: {e}")
    
    async def handle_dm_menu(self, choice: str):
        """Handle DM menu choices"""
        try:
            if choice == "1":
                dms = await self.handler.check_dms()
                print("\nNew DMs:")
                for i, dm in enumerate(dms, 1):
                    print(f"{i}. From {dm['sender']}: {dm['preview']}")
                    
            elif choice == "2":
                # TODO: Implement DM sending
                print("DM sending not yet implemented")
                
            elif choice == "3":
                # TODO: Implement DM reply
                print("DM reply not yet implemented")
                
            elif choice == "0":
                self.current_menu = "main"
                
        except Exception as e:
            logger.error(f"Error in DM menu: {e}")
    
    async def test_navigation(self):
        """Test basic navigation functions"""
        try:
            print("\nTesting navigation...")
            
            # Test home navigation
            self.handler.driver.get("https://x.com/home")
            input("Press Enter after verifying home page...")
            
            # Test profile navigation
            self.handler.driver.get("https://x.com/profile")
            input("Press Enter after verifying profile page...")
            
            # Test spaces navigation
            self.handler.driver.get("https://x.com/i/spaces")
            input("Press Enter after verifying spaces page...")
            
            print("Navigation tests completed")
            
        except Exception as e:
            logger.error(f"Error in navigation test: {e}")
    
    async def test_login_session(self):
        """Test login and session management"""
        try:
            print("\nTesting login session...")
            
            # Test logout
            # TODO: Implement logout
            
            # Test auto-login
            success = await self.handler.ensure_logged_in()
            print(f"Auto-login {'successful' if success else 'failed'}")
            
            # Test session persistence
            self.handler._save_session()
            print("Session saved")
            
            success = self.handler._load_session()
            print(f"Session load {'successful' if success else 'failed'}")
            
        except Exception as e:
            logger.error(f"Error in login session test: {e}")
    
    async def test_space_queue(self):
        """Test space queue functionality"""
        try:
            print("\nTesting space queue...")
            
            # Add test space to queue
            url = input("Enter space URL for queue test: ")
            self.handler.space_queue.add_space(url)
            
            # Process queue
            print("Processing space queue...")
            await self.handler.process_space_queue()
            
        except Exception as e:
            logger.error(f"Error in space queue test: {e}")
    
    async def test_thread_posting(self):
        """Test posting a thread"""
        try:
            print("\nTesting thread posting...")
            tweets = []
            while True:
                tweet = input("Enter tweet for thread (empty to finish): ")
                if not tweet:
                    break
                tweets.append(tweet)
            
            if tweets:
                # TODO: Implement thread posting
                print("Thread posting not yet implemented")
            
        except Exception as e:
            logger.error(f"Error in thread posting test: {e}")
    
    async def run_all_tests(self):
        """Run all available tests"""
        try:
            print("\nRunning all tests...")
            
            await self.test_navigation()
            await self.test_login_session()
            await self.test_space_queue()
            
            print("All tests completed")
            
        except Exception as e:
            logger.error(f"Error in test suite: {e}")

if __name__ == "__main__":
    tester = ManualActionTester()
    asyncio.run(tester.run()) 