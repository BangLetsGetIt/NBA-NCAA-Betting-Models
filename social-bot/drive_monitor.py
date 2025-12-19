import os
import time
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import config

SCOPES = ['https://www.googleapis.com/auth/drive']

class DriveMonitor:
    def __init__(self):
        self.creds = None
        self.service = None
        self.authenticate()

    def authenticate(self):
        """Authenticates with the Google Drive API."""
        if config.GOOGLE_TOKEN_FILE.exists():
            self.creds = Credentials.from_authorized_user_file(str(config.GOOGLE_TOKEN_FILE), SCOPES)
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(config.GOOGLE_CREDENTIALS_FILE), SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(config.GOOGLE_TOKEN_FILE, 'w') as token:
                token.write(self.creds.to_json())

        self.service = build('drive', 'v3', credentials=self.creds)

    def check_for_new_videos(self):
        """Checks the configured folder for new video files."""
        # Query for video files in the specific folder that are NOT in trashed
        query = f"'{config.DRIVE_FOLDER_ID}' in parents and mimeType contains 'video/' and trashed = false"
        results = self.service.files().list(
            q=query, pageSize=10, fields="nextPageToken, files(id, name)").execute()
        items = results.get('files', [])

        new_videos = []
        if not items:
            print("No new videos found.")
        else:
            for item in items:
                print(f"Found video: {item['name']} ({item['id']})")
                new_videos.append(item)
        return new_videos

    def download_file(self, file_id, file_name):
        """Downloads a file from Drive."""
        request = self.service.files().get_media(fileId=file_id)
        file_path = config.DOWNLOADS_DIR / file_name
        fh = io.FileIO(file_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        print(f"Downloading {file_name}...")
        while done is False:
            status, done = downloader.next_chunk()
            print(f"Download {int(status.progress() * 100)}%.")
        return file_path

    def get_or_create_processed_folder(self):
        """Finds or creates a 'Processed' folder inside the main folder."""
        query = f"'{config.DRIVE_FOLDER_ID}' in parents and name = 'Processed' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = self.service.files().list(q=query, fields="files(id)").execute()
        items = results.get('files', [])
        
        if items:
            return items[0]['id']
        else:
            # Create it
            file_metadata = {
                'name': 'Processed',
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [config.DRIVE_FOLDER_ID]
            }
            folder = self.service.files().create(body=file_metadata, fields='id').execute()
            print(f"Created 'Processed' folder with ID: {folder.get('id')}")
            return folder.get('id')

    def move_to_processed(self, file_id):
        """Moves the file to the 'Processed' subfolder."""
        processed_folder_id = self.get_or_create_processed_folder()
        
        # Retrieve the existing parents to remove
        file = self.service.files().get(fileId=file_id, fields='parents').execute()
        previous_parents = ",".join(file.get('parents'))
        
        # Move the file
        self.service.files().update(
            fileId=file_id,
            addParents=processed_folder_id,
            removeParents=previous_parents,
            fields='id, parents'
        ).execute()
        print(f"Moved file {file_id} to Processed folder.")
    
    def get_caption_for_video(self, video_name):
        """Looks for a .txt file with the same base name."""
        base_name = os.path.splitext(video_name)[0]
        query = f"'{config.DRIVE_FOLDER_ID}' in parents and name = '{base_name}.txt' and trashed = false"
        results = self.service.files().list(q=query, fields="files(id, name)").execute()
        items = results.get('files', [])
        
        if items:
            txt_file = items[0]
            txt_path = self.download_file(txt_file['id'], txt_file['name'])
            with open(txt_path, 'r') as f:
                return f.read()
        return "Check out this play! #CourtSideAnalytics" # Default caption

if __name__ == "__main__":
    monitor = DriveMonitor()
    videos = monitor.check_for_new_videos()
    for video in videos:
        # monitor.download_file(video['id'], video['name'])
        pass
