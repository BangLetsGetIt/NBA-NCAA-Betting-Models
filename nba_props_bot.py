#!/usr/bin/env python3
"""
NBA Props Bot
Analyzes YouTube videos for player props, extracts them, and generates an infographic.
"""

import os
import re
import json
import argparse
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi
from nba_api.stats.static import players, teams
from nba_api.stats.endpoints import commonplayerinfo

# Configuration
OUTPUT_HTML_PATH = os.path.expanduser("~/.gemini/antigravity/brain/1172207d-238e-4514-92d3-84209a148b77/bot_infographic.html")
# Mapping for common spoken team names/variations if needed? 
# Usually we rely on NBA API for team abbreviations.

def get_transcript_text(video_url):
    """Extracts text from a YouTube video URL."""
    try:
        if "v=" in video_url:
            video_id = video_url.split("v=")[1].split("&")[0]
        elif "youtu.be/" in video_url:
            video_id = video_url.split("youtu.be/")[1].split("?")[0]
        else:
            print("❌ Invalid YouTube URL")
            return None

        print(f"🎬 Fetching transcript for Video ID: {video_id}...")
        try:
             # Using instance method as verified for this version
             transcript = YouTubeTranscriptApi().fetch(video_id)
        except Exception as e:
             print(f"❌ Error fetching transcript: {e}")
             return None
        
        # Handle both object and dict (just in case)
        lines = []
        for entry in transcript:
            if hasattr(entry, 'text'):
                lines.append(entry.text)
            elif isinstance(entry, dict) and 'text' in entry:
                lines.append(entry['text'])
            else:
                lines.append(str(entry))
                
        full_text = " ".join(lines)
        return full_text
    except Exception as e:
        print(f"❌ Error fetching transcript: {e}")
        return None

def find_nba_players(text):
    """Finds NBA players mentioned in the text."""
    # Get all active players
    all_players = players.get_players()
    found_players = []
    
    text_lower = text.lower()
    
    print("🔍 Scanning for players...")
    for p in all_players:
        full_name = p['full_name'].lower()
        first = p['first_name'].lower()
        last = p['last_name'].lower()
        
        # Check specific nicknames
        if first == "herbert" and "herb " + last in text_lower:
             found_players.append(p)
             continue
        if first == "michael" and "mike " + last in text_lower:
             found_players.append(p)
             continue
             
        if full_name in text_lower:
            found_players.append(p)
            
    return found_players

def extract_props_for_player(text, player):
    """
    Heuristic extraction of props for a specific player.
    """
    p_name = player['full_name']
    first = player['first_name']
    last = player['last_name']
    
    text_lower = text.lower()
    
    # Try finding full name, or nickname
    name_index = text_lower.find(p_name.lower())
    if name_index == -1:
        # Try Herb Jones
        if first.lower() == "herbert":
            name_index = text_lower.find(f"herb {last.lower()}")
            
    if name_index == -1:
        return None

    # Look at a window of text
    window = text_lower[name_index:name_index+150]
    
    stat_map = {
        "points": "Pts", "pts": "Pts",
        "rebounds": "Reb", "reb": "Reb", "boards": "Reb",
        "assists": "Ast", "ast": "Ast",
        "pra": "PRA", "points, rebounds, and assists": "PRA",
        "threes": "3PM", "three-pointers": "3PM", "3pm": "3PM"
    }

    # Regex for "Over/Under" matching
    bet_type = "OVER" 
    if "under" in window or "less than" in window:
        bet_type = "UNDER"
    
    # 1. Try to find explicit lines like "17.5" or "17 and a half" or "one and a half"
    # We prioritize decimal matches or "and a half" constructs
    
    # Text to digit mapping
    word_to_num = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, 
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
        "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
        "twenty-one": 21, "twenty-two": 22, "twenty-seven": 27 # Add as needed or use a library
    }
    
    line_val = None
    
    # Regex to capture potential number patterns including words
    # Pattern: (\d+(?:\.\d+)?|one|two|...|twenty)
    # Plus optional "and a half"
    
    text_nums = "|".join(word_to_num.keys())
    # Regex: Look for number word OR digits.
    # We also check for "and a half" immediately after.
    
    # Using finditer to scan all numbers
    # We want to exclude "last 10", "90%", "9/10"
    
    # matches digits or specific words
    pattern = rf'(\b(?:\d+(?:\.\d+)?)\b|\b(?:{text_nums})\b)'
    
    matches = list(re.finditer(pattern, window))
    
    for m in matches:
        raw_val = m.group(1)
        val = 0.0
        
        # Convert to float
        if raw_val in word_to_num:
            val = float(word_to_num[raw_val])
        else:
            val = float(raw_val)
            
        # Context checks
        start_idx = m.start()
        end_idx = m.end()
        pre_context = window[max(0, start_idx-20):start_idx]
        post_context = window[end_idx:end_idx+20]
        
        # 1. Ignore "90%" or "50 percent"
        if "%" in post_context or "percent" in post_context:
            continue
            
        # 2. Ignore "last 10 games", "last 5"
        if "last" in pre_context and val in [5, 10, 20]:
            continue
            
        # 3. Ignore small integers if they look like counts not lines? 
        # But "1 rebound" or "1.5 rebounds" is valid.
        
        # Check for "and a half"
        if "and a half" in post_context:
            val += 0.5
            
        # Heuristic: If we found a valid line, use it.
        # We prefer lines that are non-integers (X.5) as they are most common props
        # If integer, we might be skeptical unless "points" is near?
        
        line_val = val
        
        # If we found a decimal or "and a half", we differnetiate it from "10 games"
        if val % 1 != 0:
            break
            
        # If it is an integer 10, 9, etc., we keep looking in case there's a better "17.5" later
        # But if it's the only number, we take it.
        # We continue looping to find best candidate?
        # Actually, closest to "Over" might be better?
        # For now, let's just break on first valid non-percent, non-last match?
        # Re-eval: Jaylen Wells ("17.5") comes before "90%".
        # Herb Jones ("one and a half") comes before "90%".
        # So "first valid" is mostly correct.
        break
        
    # Find Type
    found_stat = None
    for k, v in stat_map.items():
        if k in window:
            found_stat = v
            break
    
    # Specific check for Pts + Reb or Pts + Ast
    if ("points" in window and "rebounds" in window) and "assist" not in window:
         found_stat = "Pts + Reb"

    if line_val and found_stat:
        return {
            "player": p_name,
            "player_id": player['id'],
            "line": line_val,
            "prop": found_stat,
            "bet": bet_type
        }
    
    return None
        
    # Find Type
    found_stat = None
    for k, v in stat_map.items():
        if k in window:
            found_stat = v
            break
    
    # Specific check for Pts + Reb or Pts + Ast
    if ("points" in window and "rebounds" in window) and "assist" not in window:
         found_stat = "Pts + Reb"

    if line_val and found_stat:
        return {
            "player": p_name,
            "player_id": player['id'],
            "line": line_val,
            "prop": found_stat,
            "bet": bet_type
        }
    
    return None

def get_player_team_logo(player_id):
    """
    Fetches the team abbreviation for a player to generate the ESPN logo URL.
    """
    try:
        # This can be slow if we do it for every player 1-by-1.
        # Ideally we'd have a cache.
        info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
        data = info.get_dict()
        # commonPlayerInfo -> TeamAbbreviation
        # Structure: resultSets[0]['rowSet'][0][column_index_of_TEAM_ABBREVIATION]
        
        headers = data['resultSets'][0]['headers']
        row = data['resultSets'][0]['rowSet'][0]
        
        team_idx = headers.index('TEAM_ABBREVIATION')
        team_abbr = row[team_idx]
        
        if team_abbr:
            return f"https://a.espncdn.com/i/teamlogos/nba/500/{team_abbr.lower()}.png"
    except Exception as e:
        print(f"⚠️ Could not get team for player {player_id}: {e}")
        
    return "https://a.espncdn.com/i/teamlogos/nba/500/nba.png" # Fallback

def generate_html(plays):
    """Generates the infographic HTML."""
    
    list_items = ""
    
    for play in plays:
        logo_url = play.get('logo_url', '')
        # Formatted Line
        line_str = f"{play['line']}"
        if line_str.endswith(".0"):
            line_str = line_str[:-2]
            
        list_items += f"""
                <li class="play-item">
                    <img src="{logo_url}" class="team-logo" alt="Team Logo" onerror="this.src='https://a.espncdn.com/i/teamlogos/nba/500/nba.png'">
                    <span class="player-name">{play['player']}</span>
                    <div class="prop-details">
                         <span class="txt-green">{play['bet']}</span>
                         <span class="txt-white">{line_str}</span>
                         <span>{play['prop']}</span>
                    </div>
                </li>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bang, Let's Get It</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-main: #121212;
            --bg-card: #1e1e1e;
            --bg-card-secondary: #2a2a2a;
            --text-primary: #ffffff;
            --text-secondary: #b3b3b3;
            --accent-green: #4ade80;
            --accent-red: #f87171;
            --accent-blue: #60a5fa;
            --border-color: #333333;
        }}

        body {{
            margin: 0;
            padding: 0;
            background-color: var(--bg-main);
            font-family: 'Inter', sans-serif;
            color: var(--text-primary);
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            width: 100vw;
            box-sizing: border-box;
        }}

        .card {{
            background-color: var(--bg-card);
            width: 800px;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            border: 1px solid var(--border-color);
            position: relative;
            overflow: hidden;
        }}

        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border-color);
        }}

        h1 {{
            font-family: 'Inter', sans-serif;
            font-size: 48px;
            margin: 0;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: -1px;
            color: var(--text-primary);
        }}

        .sub-header {{
            font-size: 18px;
            color: var(--text-secondary);
            margin-top: 8px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .header-accent {{
            color: var(--accent-green);
        }}

        .section {{
            margin-bottom: 30px;
        }}

        .section-title {{
            font-family: 'Inter', sans-serif;
            font-size: 24px;
            color: var(--text-primary);
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
            font-weight: 700;
            border-left: 4px solid var(--accent-green);
            padding-left: 12px;
        }}

        .play-list {{
            list-style: none;
            padding: 0;
            margin: 0;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }}

        .play-item {{
            background-color: var(--bg-card-secondary);
            padding: 16px 20px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            font-size: 16px;
            font-weight: 600;
            border: 1px solid var(--border-color);
        }}
        
        .team-logo {{
            width: 32px;
            height: 32px;
            margin-right: 12px;
            object-fit: contain;
        }}

        .player-name {{
            color: var(--text-primary);
            margin-right: auto;
        }}

        .prop-details {{
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--text-secondary);
            font-weight: 500;
            font-size: 14px;
        }}

        .txt-green {{
            color: var(--accent-green);
            font-weight: 700;
        }}
        
        .txt-white {{
            color: var(--text-primary);
            font-weight: 700;
        }}

        .footer {{
            text-align: center;
            margin-top: 30px;
            color: var(--border-color);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <h1>BANG, LET'S GET IT</h1>
            <div class="sub-header">NBA <span class="header-accent">PROP CHEAT SHEET</span> • {datetime.now().strftime('%b %d').upper()}</div>
        </div>

        <div class="section">

            <ul class="play-list">
                {list_items}
            </ul>
        </div>
        
        <div class="footer">
            Source: Really Rico | Generated by Bot
        </div>
    </div>
</body>
</html>"""
    
    with open(OUTPUT_HTML_PATH, "w") as f:
        f.write(html_content)
    
    print(f"✅ Infographic generated info: {OUTPUT_HTML_PATH}")

def get_latest_video_url(channel_id="UClQeHSQyfwBx0HaOPuR9x7A"):
    """Fetches the latest video URL from the channel's RSS feed."""
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        import requests
        import xml.etree.ElementTree as ET
        
        print(f"📡 Checking channel feed: {channel_id}...")
        response = requests.get(rss_url, timeout=10)
        if response.status_code == 200:
            # Parse XML
            root = ET.fromstring(response.content)
            # Namespace map often needed for atom feeds
            ns = {'yt': 'http://www.youtube.com/xml/schemas/2015', 'atom': 'http://www.w3.org/2005/Atom'}
            
            # Find first entry
            entry = root.find('atom:entry', ns)
            if entry:
                # Video ID is usually in yt:videoId
                video_id = entry.find('yt:videoId', ns).text
                title = entry.find('atom:title', ns).text
                print(f"🆕 Latest Video Found: {title}")
                return f"https://www.youtube.com/watch?v={video_id}"
            else:
                print("⚠️ No entries found in feed.")
        else:
            print(f"❌ Failed to fetch feed. Status: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error checking feed: {e}")
        
    return None

def main():
    parser = argparse.ArgumentParser(description="NBA Props Video Analyzer")
    parser.add_argument("url", nargs="?", help="YouTube Video URL (optional if --latest is used)")
    parser.add_argument("--latest", action="store_true", help="Fetch latest video from @ReallyRico7")
    args = parser.parse_args()
    
    video_url = args.url
    
    if args.latest:
        video_url = get_latest_video_url()
        if not video_url:
            print("❌ Could not get latest video.")
            return
            
    if not video_url:
        print("❌ Please provide a URL or use --latest")
        return
    
    print(f"▶️ Analyze Target: {video_url}")
    text = get_transcript_text(video_url)
    if not text:
        return
        
    print("\n📝 Transcript extracted. Analyzing...")
    
    # 1. Find Players
    mentioned_players = find_nba_players(text)
    print(f"Found {len(mentioned_players)} potential players.")
    
    plays = []
    seen_players = set()
    
    # 2. Extract Props
    for p in mentioned_players:
        if p['full_name'] in seen_players:
            continue
            
        prop_data = extract_props_for_player(text, p)
        if prop_data:
            print(f"🎯 Found Play: {prop_data['player']} {prop_data['bet']} {prop_data['line']} {prop_data['prop']}")
            plays.append(prop_data)
            seen_players.add(p['full_name'])
            
    if not plays:
        print("⚠️ No specific props found. Try manually checking the video.")
        return

    # 3. Enrich with Team Logos
    print("🖼️ Fetching team logos...")
    for play in plays:
        play['logo_url'] = get_player_team_logo(play['player_id'])
        
    # 4. Generate HTML
    generate_html(plays)
    
    # Text Output
    print("\n🏀 NBA PROP CHEAT SHEET 🏀")
    for play in plays:
        print(f"✅ {play['player']}: {play['bet']} {play['line']} {play['prop']}")

if __name__ == "__main__":
    main()
