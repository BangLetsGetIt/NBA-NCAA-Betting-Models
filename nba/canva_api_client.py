#!/usr/bin/env python3
"""
Canva API Client
Handles authentication and API interactions with Canva
Uses OAuth2 authorization_code flow
"""

import os
import requests
import json
import base64
import secrets
import hashlib
from dotenv import load_dotenv
from pathlib import Path
import urllib.parse

# Load .env from project root (parent directory)
project_root = Path(__file__).parent.parent
env_path = project_root / '.env'
load_dotenv(dotenv_path=env_path)

# Canva API Configuration
CANVA_API_BASE = "https://api.canva.com/rest/v1"
CANVA_AUTH_URL = "https://api.canva.com/rest/v1/oauth/token"
CANVA_AUTHORIZE_URL = "https://www.canva.com/api/oauth/authorize"

class CanvaAPIClient:
    def __init__(self):
        self.client_id = os.getenv('CANVA_CLIENT_ID')
        self.client_secret = os.getenv('CANVA_CLIENT_SECRET')
        self.redirect_uri = os.getenv('CANVA_REDIRECT_URI', 'http://127.0.0.1:8080/callback')
        self.access_token = None
        self.refresh_token = None
        self.token_file = Path(__file__).parent / '.canva_tokens.json'
        
        if not self.client_id or not self.client_secret:
            raise ValueError("CANVA_CLIENT_ID and CANVA_CLIENT_SECRET must be set in .env file")
        
        # Load saved tokens if available
        self.load_tokens()
    
    def load_tokens(self):
        """Load saved access and refresh tokens"""
        if self.token_file.exists():
            try:
                with open(self.token_file, 'r') as f:
                    tokens = json.load(f)
                    self.access_token = tokens.get('access_token')
                    self.refresh_token = tokens.get('refresh_token')
            except:
                pass
    
    def save_tokens(self):
        """Save access and refresh tokens"""
        tokens = {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token
        }
        with open(self.token_file, 'w') as f:
            json.dump(tokens, f)
    
    def get_authorization_url(self):
        """
        Generate authorization URL for user to visit
        Returns URL and code_verifier (save this for token exchange)
        """
        # Generate PKCE parameters
        code_verifier = secrets.token_urlsafe(32)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip('=')
        
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': 'design:content:read design:content:write',
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256'
        }
        
        auth_url = f"{CANVA_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"
        return auth_url, code_verifier
    
    def exchange_code_for_token(self, authorization_code, code_verifier):
        """
        Exchange authorization code for access token
        authorization_code: Code from callback
        code_verifier: Original verifier from authorization URL
        """
        try:
            credentials = f"{self.client_id}:{self.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'grant_type': 'authorization_code',
                'code': authorization_code,
                'redirect_uri': self.redirect_uri,
                'code_verifier': code_verifier
            }
            
            response = requests.post(CANVA_AUTH_URL, data=data, headers=headers)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data.get('access_token')
            self.refresh_token = token_data.get('refresh_token')
            
            if not self.access_token:
                raise ValueError("Failed to get access token from Canva API")
            
            self.save_tokens()
            print("✓ Successfully authenticated with Canva API")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Authentication error: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"  Response: {e.response.text}")
            return False
    
    def refresh_access_token(self):
        """Refresh access token using refresh token"""
        if not self.refresh_token:
            print("✗ No refresh token available. Need to re-authorize.")
            return False
        
        try:
            credentials = f"{self.client_id}:{self.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token
            }
            
            response = requests.post(CANVA_AUTH_URL, data=data, headers=headers)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data.get('access_token')
            self.refresh_token = token_data.get('refresh_token', self.refresh_token)
            
            if not self.access_token:
                raise ValueError("Failed to refresh access token")
            
            self.save_tokens()
            print("✓ Successfully refreshed access token")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Token refresh error: {e}")
            # Clear tokens if refresh fails
            self.access_token = None
            self.refresh_token = None
            if self.token_file.exists():
                self.token_file.unlink()
            return False
    
    def get_headers(self):
        """Get headers for API requests"""
        if not self.access_token:
            # Try to refresh first
            if not self.refresh_access_token():
                raise ValueError("No valid access token. Please re-authorize.")
        
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
    
    def create_design(self, template_id=None, design_data=None):
        """
        Create a new design in Canva
        template_id: Optional template ID to use
        design_data: Dictionary with design content
        """
        headers = self.get_headers()
        url = f"{CANVA_API_BASE}/designs"
        
        # URL encode template_id if provided
        if template_id:
            template_id = urllib.parse.quote(template_id, safe='')
        
        payload = {}
        if template_id:
            payload['template_id'] = template_id
        if design_data:
            payload.update(design_data)
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"✗ Error creating design: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"  Response: {e.response.text}")
            return None
    
    def update_design(self, design_id, updates):
        """Update an existing design"""
        headers = self.get_headers()
        url = f"{CANVA_API_BASE}/designs/{design_id}"
        
        try:
            response = requests.patch(url, headers=headers, json=updates)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"✗ Error updating design: {e}")
            return None
    
    def export_design(self, design_id, format='png'):
        """
        Export a design as an image
        format: 'png', 'jpg', 'pdf'
        """
        headers = self.get_headers()
        url = f"{CANVA_API_BASE}/designs/{design_id}/exports"
        
        payload = {
            'format': format,
            'quality': 'high'
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"✗ Error exporting design: {e}")
            return None
    
    def get_design_url(self, design_id):
        """Get the URL to view/edit a design"""
        return f"https://www.canva.com/design/{design_id}/view"
    
    def is_authenticated(self):
        """Check if we have a valid access token"""
        return self.access_token is not None
    
    def test_connection(self):
        """Test the API connection"""
        print("\nTesting Canva API connection...")
        
        if not self.is_authenticated():
            print("✗ Not authenticated. Need to authorize first.")
            print("\nTo authorize:")
            print("1. Run: python3 nba/authorize_canva.py")
            print("2. Follow the instructions to authorize the app")
            return False
        
        # Try a simple API call to test
        try:
            headers = self.get_headers()
            # Test with a simple endpoint (if available)
            print("✓ Access token is valid")
            return True
        except Exception as e:
            print(f"✗ Connection test failed: {e}")
            return False
