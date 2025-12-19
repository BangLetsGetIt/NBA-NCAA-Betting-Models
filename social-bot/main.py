import time
import schedule
import config
from drive_monitor import DriveMonitor
from platforms.tiktok import TikTokPoster
from platforms.x import XPoster
from platforms.instagram import InstagramPoster

def job():
    print("\n[Job] Checking for new content...")
    monitor = DriveMonitor()
    
    # Check for new videos
    new_videos = monitor.check_for_new_videos()
    
    if not new_videos:
        return

    # Initialize posters (only if we have content, to save resources)
    tiktok = TikTokPoster()
    x = XPoster()
    insta = InstagramPoster()

    # Pre-load cookies
    # In a real run, we might want to check cookie validity first
    
    for video in new_videos:
        print(f"Processing {video['name']}...")
        
        # 1. Download
        video_path = monitor.download_file(video['id'], video['name'])
        caption = monitor.get_caption_for_video(video['name'])
        
        # 2. Post to TikTok
        print(" Posting to TikTok...")
        try:
            tiktok.login()
            tiktok.upload_video(video_path, caption)
        except Exception as e:
            print(f"TikTok upload failed: {e}")
        finally:
            tiktok.quit()

        # 3. Post to X
        print(" Posting to X...")
        try:
            x.login()
            x.upload_video(video_path, caption)
        except Exception as e:
            print(f"X upload failed: {e}")
        finally:
            x.quit()

        # 4. Post to Instagram
        print(" Posting to Instagram...")
        try:
            insta.login()
            insta.upload_video(video_path, caption)
        except Exception as e:
            print(f"Instagram upload failed: {e}")
        finally:
            insta.quit()

        # 5. Cleanup / Move to Processed
        try:
            monitor.move_to_processed(video['id']) 
            # Check if there is a caption file and move it too?
            # Ideally yes, but sticking to video for now.
        except Exception as e:
            print(f"Failed to move file to Processed: {e}")

        print(f"Finished processing {video['name']}")

def main():
    print("CourtSide Analytics Bot Started.")
    print("Watching Google Drive for new videos...")
    
    # Run immediately on start
    job()
    
    # Then schedule every 15 minutes
    schedule.every(15).minutes.do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
