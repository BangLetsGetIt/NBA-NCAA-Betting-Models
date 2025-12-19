import time
from selenium.webdriver.common.by import By
from browser_engine import BrowserEngine

class InstagramPoster(BrowserEngine):
    def __init__(self):
        super().__init__("instagram")
        self.base_url = "https://www.instagram.com/"

    def login(self):
        self.load_cookies(self.base_url)
        # Dismiss "Turn on Notifications" modal if it appears
        time.sleep(5)
        try:
            self.driver.find_element(By.XPATH, "//button[contains(text(), 'Not Now')]").click()
        except:
            pass

    def upload_video(self, video_path, caption):
        self.open_page(self.base_url)
        time.sleep(5)

        try:
            # 1. Click 'Create' (+) button on the sidebar
            create_btn = self.driver.find_element(By.XPATH, "//*[contains(@aria-label, 'New post')]")
            create_btn.click()
            time.sleep(2)

            # 2. Upload file
            # There should be an input type=file now in the modal
            # It might be created dynamically
            file_input = self.driver.find_element(By.XPATH, "//form//input[@type='file']")
            file_input.send_keys(str(video_path))
            print("Video uploaded...")
            time.sleep(5)

            # 3. Handle Crop/Next flow (Instagram desktop has a modal wizard)
            # Click 'Next' (Crop)
            next_btn = self.driver.find_element(By.XPATH, "//div[text()='Next']")
            next_btn.click()
            time.sleep(2)
            
            # Click 'Next' (Filter)
            next_btn = self.driver.find_element(By.XPATH, "//div[text()='Next']")
            next_btn.click()
            time.sleep(2)

            # 4. Add Caption
            caption_area = self.driver.find_element(By.XPATH, "//div[@aria-label='Write a caption...']")
            caption_area.click()
            caption_area.send_keys(caption)
            print("Caption added.")

            # 5. Share
            share_btn = self.driver.find_element(By.XPATH, "//div[text()='Share']")
            share_btn.click()
            print("Shared to Instagram!")
            
            time.sleep(10) # Wait for upload to finish
            return True
        except Exception as e:
            print(f"Error posting to Instagram: {e}")
            return False
