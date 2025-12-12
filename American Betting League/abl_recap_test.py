import pandas as pd
import jinja2
import ssl
import os
from datetime import datetime
import shutil
import plotly.express as px
import plotly.io as pio

# --- Configuration ---
BASE_SHEET_URL = 'https://docs.google.com/spreadsheets/d/1n_fAOu2dbT9DavwD7Kq12QJ8an7X4LBdP6o3-2_A2pA/export?format=csv'
# Add a cache-busting timestamp to the URL to always get fresh data
SHEET_URL = f"{BASE_SHEET_URL}&_={int(datetime.now().timestamp())}"
IMAGES_FOLDER = 'images'
HISTORY_FOLDER = 'history'
OUTPUT_FILE = 'dashboard.html'
UNIT_GLOW_THRESHOLD = 5
HUGE_GAIN_THRESHOLD = 5
TOP_RISERS_COUNT = 5
TREND_DAYS = 5  # last N days for sparkline

# --- HTML Template ---
HTML_TEMPLATE = """ 
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>American Betting League Standings</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>
body { background: #000; color: #fff; }
.streak-w { color: #22c55e; font-weight: 600; }
.streak-l { color: #ef4444; font-weight: 600; }
.unit-positive { color: #22c55e; }
.unit-negative { color: #ef4444; }
.rank-top-3 { font-weight: 900; color: #f59e0b; }
.dynamic-glow { animation: glow 1.5s ease-in-out infinite alternate; border-color: #f59e0b; }
@keyframes glow { 0% { box-shadow: 0 0 15px rgba(250,204,21,0.3); } 50% { box-shadow:0 0 25px rgba(250,204,21,0.6); } 100% { box-shadow:0 0 15px rgba(250,204,21,0.3); } }
.box { background: #111; border:1px solid #333; border-radius:0.5rem; padding:1rem; }
.box:hover { background: #222; }
img.screenshot { border-radius: 0.5rem; box-shadow: 0 0 10px rgba(255,255,255,0.1); transition: transform 0.3s ease; }
img.screenshot:hover { transform: scale(1.02); }
.sparkline { height: 40px; width: 100%; }
table th, table td { border-color: #333; }
</style>
</head>
<body class="font-sans p-4 md:p-8">
<div class="max-w-7xl mx-auto">
<header class="mb-8">
<h1 class="text-4xl md:text-5xl font-extrabold text-white mb-2">American Betting League</h1>
<p class="text-xl text-gray-400">Official Standings & Multi-Day Report</p>
<p class="text-sm text-gray-500 mt-2">Last Updated: {{ last_updated }}</p>
</header>

<div class="grid grid-cols-1 lg:grid-cols-3 gap-8">

<div class="lg:col-span-2">
<div class="box shadow-2xl overflow-hidden">
<div class="overflow-x-auto">
<table class="min-w-full divide-y divide-gray-800">
<thead class="bg-black"> <tr>
<th class="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Rank</th>
<th class="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Bettor</th>
<th class="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Unit</th>
<th class="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Record (W-L-P)</th>
<th class="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Win %</th>
<th class="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Streak</th>
<th class="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Units Yesterday</th>
<th class="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Record Yesterday</th>
<th class="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Trend (Last {{ TREND_DAYS }} Days)</th>
</tr>
</thead>
<tbody class="divide-y divide-gray-800">
{% for row in data %}
<tr class="hover:bg-gray-800 transition-colors duration-150">
<td class="px-4 py-4 text-sm {{ 'rank-top-3' if row['RANK'] <= 3 else '' }}">{{ row['RANK'] }}</td>
<td class="px-4 py-4 text-sm font-medium text-white">{{ row['BETTOR'] }}</td>
<td class="px-4 py-4 text-sm {{ 'unit-positive' if row['UNIT'] > 0 else 'unit-negative' }}">{{ "%.2f"|format(row['UNIT']) }}</td>
<td class="px-4 py-4 text-sm text-gray-300">{{ row['W'] }}-{{ row['L'] }}-{{ row['P'] }}</td>
<td class="px-4 py-4 text-sm text-gray-300">{{ row['%'] }}</td>
<td class="px-4 py-4 text-sm {{ 'streak-w' if 'W' in row['STRK'] else ('streak-l' if 'L' in row['STRK'] else '') }}">{{ row['STRK'] }}</td>
<td class="px-4 py-4 text-sm {{ 'unit-positive' if row['LDAY UNITS'] > 0 else ('unit-negative' if row['LDAY UNITS'] < 0 else '') }}">{{ "%.2f"|format(row['LDAY UNITS']) }}</td>
<td class="px-4 py-4 text-sm text-gray-300">{{ row['LDAY REC'] }}</td>
<td class="px-4 py-4 text-sm">{{ row['sparkline']|safe }}</td>
</tr>
{% endfor %}
</tbody>
</table>
</div>
</div>
</div>

<div class="lg:col-span-1 space-y-6">

<div class="box shadow-2xl {{ 'dynamic-glow' if bettor_of_day['LDAY UNITS'] >= UNIT_GLOW_THRESHOLD else '' }}">
<h2 class="text-2xl font-bold text-yellow-400 mb-4">🏆 Bettor of The Day</h2>
<p class="text-2xl font-semibold text-white">{{ bettor_of_day['BETTOR'] }}</p>
<p class="text-sm text-gray-400 mb-2">Rank #{{ bettor_of_day['RANK'] }}</p>
<p class="text-gray-300 mt-2">Units Yesterday: <span class="{{ 'unit-positive' if bettor_of_day['LDAY UNITS'] > 0 else 'unit-negative' }}">{{ "%.2f"|format(bettor_of_day['LDAY UNITS']) }}</span></p>
<p class="text-yellow-400 font-semibold text-md mt-1">Total Units: {{ "%.2f"|format(bettor_of_day['UNIT']) }}</p>
</div>

<div class="box border-green-600 shadow-2xl">
<h2 class="text-2xl font-bold text-green-400 mb-4">📈 Biggest Risers</h2>
{% if movers %}
<ul class="space-y-3">
{% for m in movers %}
<li class="text-sm text-gray-200">
🟩 <span class="font-semibold">{{ m['BETTOR'] }}</span>
{% if m.huge_gain %}<span class="text-yellow-400 font-bold ml-1">🏅</span>{% endif %}
{% if m['rank_change'] > 0 %} jumped <span class="text-green-400 font-bold">+{{ m['rank_change'] }}</span> ranks{% endif %}
{% if m['unit_change'] > 0 %} and gained <span class="text-green-400 font-bold">+{{ "%.2f"|format(m['unit_change']) }}</span> units{% endif %}
<div class="sparkline">{{ m['sparkline']|safe }}</div>
</li>
{% endfor %}
</ul>
{% else %}
<p class="text-gray-400">No positive rank or unit changes detected.</p>
{% endif %}
</div>

<div class="box">
<h2 class="text-2xl font-bold text-white mb-4">Top Performers</h2>
{% if images %}
<div class="grid grid-cols-1 gap-4">
{% for img in images %}
<img src="{{ img }}" alt="Screenshot" class="screenshot w-full h-auto" loading="lazy">
{% endfor %}
</div>
{% else %}
<p class="text-gray-400">No screenshots uploaded yet.</p>
{% endif %}
</div>

</div>
</div>
</div>
</body>
</html>
"""

# --- Main Script ---
def create_dashboard():
    ssl._create_default_https_context = ssl._create_unverified_context
    os.makedirs(HISTORY_FOLDER, exist_ok=True)
    os.makedirs(IMAGES_FOLDER, exist_ok=True)

    try:
        # Load today's data
        data = pd.read_csv(SHEET_URL)
    except Exception as e:
        print(f"FATAL ERROR: Could not download or read Google Sheet. {e}")
        return

    # Fill blanks in LDAY REC column so it doesn't show "nan"
    if 'LDAY REC' in data.columns:
        data['LDAY REC'] = data['LDAY REC'].fillna('N/A')
    
    # --- START OF THE FIX ---
    # This force-cleans the data from the sheet.
    
    # First, make sure all essential columns exist
    # Added 'LDAY REC' to this check
    for col in ['UNIT', 'RANK', 'LDAY UNITS', 'BETTOR', 'LDAY REC']:
        if col not in data.columns:
            print(f"FATAL ERROR: Column '{col}' not found in your Google Sheet. Please check spelling.")
            # Create a dummy column if LDAY REC is the one missing so script can run
            if col == 'LDAY REC':
                 data['LDAY REC'] = 'N/A'
                 print(f"Warning: 'LDAY REC' column created as dummy.")
            else:
                return # Exit if essential columns (UNIT, RANK, etc.) are missing
            
    # Clean NUMERIC columns
    numeric_cols = ['UNIT', 'RANK', 'LDAY UNITS']
    for col in numeric_cols:
        data[col] = data[col].astype(str)
        # Use regex to strip out bad characters. Keep numbers, '.', and '-'
        data[col] = data[col].replace(r'[^\d.-]', '', regex=True)
        # Now, convert to numeric. 'coerce' turns any leftover blanks (from empty cells) into 0.
        data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0)
    
    # --- END OF THE FIX ---

    # --- DEBUGGING LINES ---
    print("--- DEBUG: Data *After* Force-Cleaning ---")
    print(data[['BETTOR', 'LDAY UNITS', 'LDAY REC']].head())
    print("-----------------------------------------")
    # --- END DEBUG ---
       
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_file = os.path.join(HISTORY_FOLDER, f"{today_str}.csv")
    data.to_csv(today_file, index=False)

    # Last N days for trends
    history_files = sorted([os.path.join(HISTORY_FOLDER,f) for f in os.listdir(HISTORY_FOLDER)
                            if f.endswith('.csv')])[-TREND_DAYS:]
    trends = {}
    if history_files:
        for f in history_files:
            try:
                df = pd.read_csv(f)
                for _, row in df.iterrows():
                    trends.setdefault(row['BETTOR'], []).append(row['UNIT'])
            except Exception as e:
                print(f"Warning: Could not read history file {f}. {e}")

    # Build sparklines
    spark_dict = {}
    for bettor, units_list in trends.items():
        if len(units_list) > 1: # Need at least 2 points for a line
            fig = px.line(y=units_list, height=40)
            fig.update_traces(line_color="#22c55e", mode="lines") # Removed markers for cleaner look
            fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), xaxis=dict(visible=False),
                              yaxis=dict(visible=False), paper_bgcolor='rgba(0,0,0,0)',
                              plot_bgcolor='rgba(0,0,0,0)')
            spark_html = pio.to_html(fig, include_plotlyjs=False, full_html=False)
            spark_dict[bettor] = spark_html
    data['sparkline'] = data['BETTOR'].map(spark_dict).fillna("")


    # Bettor of the Day
    # Handle case where all LDAY UNITS are 0
    if data['LDAY UNITS'].max() > 0:
        bettor_of_day = data.loc[data['LDAY UNITS'].idxmax()].to_dict()
    else:
        bettor_of_day = {'BETTOR': 'N/A', 'LDAY UNITS': 0, 'UNIT': 0, 'RANK': 0}


    # Biggest Risers
    movers = []
    if len(history_files) >= 2:
        try:
            prev_df = pd.read_csv(history_files[-2])
            # Clean previous data just in case
            prev_df['RANK'] = pd.to_numeric(prev_df['RANK'], errors='coerce').fillna(0)
            prev_df['UNIT'] = pd.to_numeric(prev_df['UNIT'], errors='coerce').fillna(0)
            
            merged = pd.merge(data, prev_df, on='BETTOR', suffixes=('', '_prev'))
            merged['rank_change'] = merged['RANK_prev'] - merged['RANK']
            merged['unit_change'] = merged['UNIT'] - merged['UNIT_prev']
            
            movers_df = merged[(merged['rank_change']>0) | (merged['unit_change']>0)].sort_values(['rank_change','unit_change'],ascending=False).head(TOP_RISERS_COUNT)
            
            for _, row in movers_df.iterrows():
                spark_html = ""
                units_list = trends.get(row['BETTOR'], [])
                if len(units_list) > 1:
                    fig = px.line(y=units_list, height=40)
                    fig.update_traces(line_color="#22c55e", mode="lines")
                    fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), xaxis=dict(visible=False),
                                      yaxis=dict(visible=False), paper_bgcolor='rgba(0,0,0,0)',
                                      plot_bgcolor='rgba(0,0,0,0)')
                    spark_html = pio.to_html(fig, include_plotlyjs=False, full_html=False)
                
                movers.append({
                    'BETTOR': row['BETTOR'],
                    'rank_change': int(row['rank_change']),
                    'unit_change': float(row['unit_change']),
                    'sparkline': spark_html,
                    'huge_gain': row['unit_change'] >= HUGE_GAIN_THRESHOLD
                })
        except Exception as e:
            print(f"Warning: Could not process 'Biggest Risers'. {e}")

    # Screenshots
    images = [os.path.join(IMAGES_FOLDER,f) for f in os.listdir(IMAGES_FOLDER)
              if os.path.isfile(os.path.join(IMAGES_FOLDER,f)) and f.lower().endswith(('.png','.jpg','.jpeg'))]

    # Render HTML
    env = jinja2.Environment(loader=jinja2.BaseLoader())
    html = env.from_string(HTML_TEMPLATE).render(
        data=data.to_dict('records'),
        bettor_of_day=bettor_of_day,
        movers=movers,
        images=images,
        last_updated=datetime.now().strftime("%B %d, %Y at %I:%M %p"),
        UNIT_GLOW_THRESHOLD=UNIT_GLOW_THRESHOLD,
        TREND_DAYS=TREND_DAYS
    )

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"🎉 Dashboard updated! Open this *exact* file: {os.path.abspath(OUTPUT_FILE)}")

if __name__ == "__main__":
    create_dashboard()