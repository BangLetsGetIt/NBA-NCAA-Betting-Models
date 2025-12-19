import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from browser_engine import BrowserEngine

class XPoster(BrowserEngine):
    def __init__(self):
        super().__init__("x")
        self.base_url = "https://twitter.com/home"

    def login(self):
        self.load_cookies(self.base_url)

    def upload_video(self, video_path, caption):
        self.open_page(self.base_url)
        time.sleep(5)

        try:
            # 1. Find the file input for media
            # X/Twitter usually has a hidden file input for the media button
            file_input = self.driver.find_element(By.XPATH, "//input[@type='file']")
            file_input.send_keys(str(video_path))
            print("Video attached...")
            
            time.sleep(5) # Wait for processing

            # 2. Add Caption
            # The tweet composer
            tweet_box = self.driver.find_element(By.XPATH, "//div[@data-testid='tweetTextarea_0']")
            tweet_box.click()
            tweet_box.send_keys(caption)
            print("Caption added.")

            # 3. Click Post
            post_btn = self.driver.find_element(By.XPATH, "//div[@data-testid='tweetButtonInline']")
            post_btn.click()
            print("Posted to X!")
            
            time.sleep(5)
            return True
        except Exception as e:
            print(f"Error posting to X: {e}")
            return False
