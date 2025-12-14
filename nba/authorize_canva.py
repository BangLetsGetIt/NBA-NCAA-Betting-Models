#!/usr/bin/env python3
"""
Canva Authorization Script
Handles the OAuth flow to authorize Canva API access
"""

import sys
from canva_api_client import CanvaAPIClient
import http.server
import socketserver
import urllib.parse
from urllib.parse import urlparse, parse_qs

# Store code_verifier globally for callback
code_verifier = None

class CallbackHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        global code_verifier
        
        # Parse the callback URL
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        
        if 'code' in params:
            auth_code = params['code'][0]
            
            # Exchange code for token
            client = CanvaAPIClient()
            if client.exchange_code_for_token(auth_code, code_verifier):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                html = """
                    <html>
                    <body style="font-family: Arial; text-align: center; padding: 50px;">
                        <h1 style="color: #00C4CC;">✓ Authorization Successful!</h1>
                        <p>You can close this window and return to the terminal.</p>
                        <p style="color: #666;">Your Canva API access is now configured.</p>
                    </body>
                    </html>
                """
                self.wfile.write(html.encode())
                # Stop the server
                import threading
                threading.Thread(target=self.server.shutdown).start()
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"<h1>Authorization Failed</h1><p>Check the terminal for details.</p>")
        elif 'error' in params:
            error = params['error'][0]
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(f"<h1>Authorization Error</h1><p>{error}</p>".encode())
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<h1>Invalid Request</h1>")
    
    def log_message(self, format, *args):
        # Suppress server logs
        pass

def authorize_canva():
    """Run the OAuth authorization flow"""
    global code_verifier
    
    print("\n" + "="*60)
    print("Canva API Authorization")
    print("="*60 + "\n")
    
    client = CanvaAPIClient()
    
    # Check if already authorized
    if client.is_authenticated():
        print("✓ Already authorized!")
        print("  Access token is valid.")
        return True
    
    # Get authorization URL
    auth_url, code_verifier = client.get_authorization_url()
    
    print("Step 1: Authorize this app in your browser")
    print("-" * 60)
    print(f"\nVisit this URL:\n\n{auth_url}\n")
    print("-" * 60)
    print("\nStep 2: Waiting for authorization callback...")
    print("(A browser window will open automatically)\n")
    
    # Start local server to receive callback
    PORT = 8080
    
    try:
        # Try to open browser automatically
        import webbrowser
        webbrowser.open(auth_url)
        print("✓ Browser opened. Please authorize the app.\n")
    except:
        print("⚠  Could not open browser automatically.")
        print("   Please copy and paste the URL above into your browser.\n")
    
    # Start callback server
    with socketserver.TCPServer(("", PORT), CallbackHandler) as httpd:
        print(f"✓ Callback server running on http://localhost:{PORT}")
        print("   Waiting for authorization...\n")
        httpd.timeout = 300  # 5 minute timeout
        httpd.handle_request()
    
    # Check if authorization succeeded
    if client.is_authenticated():
        print("\n" + "="*60)
        print("✓ Authorization Complete!")
        print("="*60)
        print("\nYour Canva API access is now configured.")
        print("You can now generate cards using Canva.\n")
        return True
    else:
        print("\n" + "="*60)
        print("✗ Authorization Failed")
        print("="*60)
        print("\nPlease try again or use PIL/Pillow for card generation.\n")
        return False

if __name__ == "__main__":
    authorize_canva()
