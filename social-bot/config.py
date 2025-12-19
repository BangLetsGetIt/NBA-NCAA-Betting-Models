import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
ARCHIVE_DIR = BASE_DIR / "archive"
COOKIES_DIR = BASE_DIR / "cookies"

# Create directories if they don't exist
DOWNLOADS_DIR.mkdir(exist_ok=True)
ARCHIVE_DIR.mkdir(exist_ok=True)
COOKIES_DIR.mkdir(exist_ok=True)

# Google Drive Config
# You need to download 'credentials.json' from Google Cloud Console and place it in the social-bot folder
GOOGLE_CREDENTIALS_FILE = BASE_DIR / "credentials.json"
GOOGLE_TOKEN_FILE = BASE_DIR / "token.json"
# The ID of the folder in Google Drive to watch
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "1Y6m-xUUxj5lHBqx6x-7wsLQHSkHwJd59") 

# Social Media Credentials (if needed for headless login, but cookies are preferred)
TIKTOK_USERNAME = os.getenv("TIKTOK_USERNAME")
TIKTOK_PASSWORD = os.getenv("TIKTOK_PASSWORD")
X_USERNAME = os.getenv("X_USERNAME")
X_PASSWORD = os.getenv("X_PASSWORD")
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")

# Browser Config
HEADLESS = False  # Set to True for production background running
BROWSER_TYPE = "chrome" 
