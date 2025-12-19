import time
from platforms.tiktok import TikTokPoster
from platforms.x import XPoster
from platforms.instagram import InstagramPoster

def setup_platform(platform_class, name):
    print(f"\n--- Setting up {name} ---")
    bot = platform_class()
    bot.start_browser()
    bot.open_page(bot.driver.current_url if bot.driver.current_url != "data:," else "https://google.com")
    
    if name == "TikTok":
        bot.open_page("https://www.tiktok.com/login")
    elif name == "X":
        bot.open_page("https://twitter.com/login")
    elif name == "Instagram":
        bot.open_page("https://www.instagram.com/accounts/login/")

    print(f"Browser opened for {name}. Please log in manually.")
    input("Press ENTER here once you are successfully logged in and on the home page...")
    
    bot.save_cookies()
    print(f"Saved cookies for {name}.")
    bot.quit()

def main():
    print("Welcome to CourtSide Analytics Bot Setup")
    print("This script will open a browser for each platform so you can log in.")
    print("Your session (cookies) will be saved so the bot can run automatically later.")
    
    if input("Setup TikTok? (y/n): ").lower() == 'y':
        setup_platform(TikTokPoster, "TikTok")
        
    if input("Setup X (Twitter)? (y/n): ").lower() == 'y':
        setup_platform(XPoster, "X")
        
    if input("Setup Instagram? (y/n): ").lower() == 'y':
        setup_platform(InstagramPoster, "Instagram")

    print("\nSetup complete! You can now run 'python main.py' to start the bot.")

if __name__ == "__main__":
    main()
