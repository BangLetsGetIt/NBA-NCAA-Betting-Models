import pickle
import time
import os
from pathlib import Path
import undetected_chromedriver as uc
import config

class BrowserEngine:
    def __init__(self, platform_name):
        self.platform_name = platform_name
        self.driver = None
        self.cookies_path = config.COOKIES_DIR / f"{platform_name}_cookies.pkl"

    def start_browser(self):
        """Initializes the Undetected Chrome WebDriver."""
        options = uc.ChromeOptions()
        if config.HEADLESS:
            options.add_argument("--headless")
        
        options.add_argument("--no-sandbox")
        # options.add_argument("--disable-dev-shm-usage") # uc often handles this
        options.add_argument("--start-maximized")
        
        # Persistence: Use a local profile so X/TikTok see us as a returning device
        # Note: uc handles profile slightly differently, but user-data-dir is standard
        profile_dir = config.BASE_DIR / "chrome_profile"
        options.add_argument(f"--user-data-dir={profile_dir}")

        # undetected-chromedriver handles driver downloading and patching automatically
        self.driver = uc.Chrome(options=options, use_subprocess=True)

    def open_page(self, url):
        if not self.driver:
            self.start_browser()
        self.driver.get(url)

    def save_cookies(self):
        """Saves current cookies to a file."""
        if self.driver:
            pickle.dump(self.driver.get_cookies(), open(self.cookies_path, "wb"))
            print(f"[{self.platform_name}] Cookies saved.")

    def load_cookies(self, url):
        """Loads cookies from file if they exist."""
        if self.cookies_path.exists():
            # We must be on the domain to set cookies
            self.open_page(url)
            cookies = pickle.load(open(self.cookies_path, "rb"))
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    # Some cookies might fail if domain mismatch, ignore
                    pass
            print(f"[{self.platform_name}] Cookies loaded.")
            self.driver.refresh()
        else:
            print(f"[{self.platform_name}] No cookies found. Please log in manually.")

    def quit(self):
        if self.driver:
            self.driver.quit()
