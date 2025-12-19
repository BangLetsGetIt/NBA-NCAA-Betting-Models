import time
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from browser_engine import BrowserEngine

class TikTokPoster(BrowserEngine):
    def __init__(self):
        super().__init__("tiktok")
        self.upload_url = "https://www.tiktok.com/upload?lang=en"

    def login(self):
        """
        Logs in by loading cookies or prompting user.
        TikTok login is CAPTCHA heavy, so we rely 100% on manual login first.
        """
        self.load_cookies("https://www.tiktok.com/")
        # specific check to see if logged in could be added here
    
    def upload_video(self, video_path, caption):
        self.open_page(self.upload_url)
        time.sleep(5) # Let page load

        # 1. Upload Video
        # We need to find the input type='file'
        try:
            # This selector is common but TikTok changes it. 
            # Often it's hidden, so we just send keys to the input element regardless of visibility
            file_input = self.driver.find_element(By.XPATH, "//input[@type='file']")
            file_input.send_keys(str(video_path))
            print("Video uploading...")
        except Exception as e:
            print(f"Error finding file input: {e}")
            return False

        # Wait for upload to complete (simplified logic)
        # In a real robust bot, we'd watch for the progress bar or the "Change video" text
        time.sleep(20) 

        # 2. Add Caption
        try:
            # The caption area is usually a contenteditable div
            # Warning: Selectors are fragile
            caption_box = self.driver.find_element(By.XPATH, "//div[contains(@class, 'notranslate public-DraftEditor-content')]")
            caption_box.click()
            caption_box.send_keys(caption)
            print("Caption added.")
        except Exception as e:
            print(f"Error finding caption box: {e}")
            # Try fallback selector
            pass

        # 3. Click Post
        try:
            # Look for a button with text 'Post'
            post_btn = self.driver.find_element(By.XPATH, "//button//div[text()='Post']")
            # Scroll into view
            self.driver.execute_script("arguments[0].scrollIntoView();", post_btn)
            time.sleep(1)
            post_btn.click()
            print("Clicked Post!")
            
            # Wait for confirmation
            time.sleep(10)
        except Exception as e:
            print(f"Error finding Post button: {e}")
            return False

        return True
