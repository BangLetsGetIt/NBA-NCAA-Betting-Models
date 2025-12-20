#!/usr/bin/env python3
"""
American Betting League Dashboard Generator - AUTOMATED EDITION
Matches CourtSide Analytics Premium Aesthetic (Blue/Green/Dark)
"""

import pandas as pd
import jinja2
import ssl
import os
from datetime import datetime
import plotly.express as px
import plotly.io as pio

# --- Configuration ---
BASE_SHEET_URL = 'https://docs.google.com/spreadsheets/d/1n_fAOu2dbT9DavwD7Kq12QJ8an7X4LBdP6o3-2_A2pA/export?format=csv'
SHEET_URL = f"{BASE_SHEET_URL}&_={int(datetime.now().timestamp())}"
HISTORY_FOLDER = 'history'
OUTPUT_FILE = 'dashboard.html'

# --- CSS & HTML Template ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ABL Midseason Update</title>
    <!-- Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-main: #121212;
            --bg-card: #1e1e1e;
            --bg-card-secondary: #2a2a2a;
            --text-primary: #ffffff;
            --text-secondary: #b3b3b3;
            --accent-green: #228B22;
            --accent-green-dim: rgba(34, 139, 34, 0.15);
            --accent-red: #f87171;
            --accent-blue: #3b82f6; /* Modern Blue */
            --accent-blue-dim: rgba(59, 130, 246, 0.1);
            --border-color: #333333;
        }

        body {
            background-color: var(--bg-main);
            color: var(--text-primary);
            font-family: 'Inter', sans-serif;
            margin: 0;
            padding: 20px;
            line-height: 1.5;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        /* --- Header --- */
        header {
            text-align: center;
            margin-bottom: 50px;
            padding: 40px 0;
            border-bottom: 1px solid var(--border-color);
        }

        h1 {
            font-size: 3.5rem;
            font-weight: 900;
            margin: 0;
            color: #fff;
            text-transform: uppercase;
            letter-spacing: -1px;
        }

        .subtitle {
            font-size: 1.25rem;
            color: var(--accent-blue);
            margin-top: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 2px;
        }

        .date-badge {
            display: inline-block;
            background: var(--bg-card-secondary);
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin-top: 20px;
            font-weight: 500;
        }

        /* --- Sections --- */
        .section-title {
            font-size: 1.25rem;
            font-weight: 700;
            margin-bottom: 25px;
            display: flex;
            align-items: center;
            color: #fff;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .section-title::before {
            content: '';
            display: inline-block;
            width: 6px;
            height: 24px;
            background: var(--accent-blue);
            margin-right: 12px;
            border-radius: 2px;
        }

        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 50px; }
        
        @media (max-width: 768px) {
            .grid-2 { grid-template-columns: 1fr; }
        }

        /* --- Cards --- */
        .card {
            background: var(--bg-card);
            border-radius: 12px;
            padding: 24px;
            border: 1px solid var(--border-color);
        }

        /* --- Performer Lists --- */
        .performer-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }

        .performer-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 0;
            border-bottom: 1px solid var(--border-color);
        }
        .performer-item:last-child { border-bottom: none; }

        .p-rank {
            font-size: 0.9rem;
            color: var(--text-secondary);
            width: 30px;
            font-weight: 600;
        }
        
        .p-info { flex-grow: 1; }
        .p-name { font-weight: 700; font-size: 1.1rem; color: #fff; display: block; }
        .p-sub { font-size: 0.85rem; color: var(--text-secondary); margin-top: 4px; }

        .p-stat { text-align: right; }
        .p-val { font-size: 1.2rem; font-weight: 800; display: block; }
        .p-lbl { font-size: 0.75rem; color: var(--text-secondary); text-transform: uppercase; }

        /* --- Badges --- */
        .badge-top { background: var(--accent-green-dim); color: var(--accent-green); padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; }
        .badge-steady { background: var(--accent-blue-dim); color: var(--accent-blue); padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; }

        /* --- Chart --- */
        .chart-container {
            width: 100%;
            height: 400px;
            border-radius: 8px;
            overflow: hidden;
        }

        /* --- Table --- */
        .standings-container {
            overflow-x: auto;
            background: var(--bg-card);
            border-radius: 12px;
            border: 1px solid var(--border-color);
        }

        table { width: 100%; border-collapse: collapse; }
        th {
            background: var(--bg-card-secondary);
            text-align: left;
            padding: 14px 20px;
            font-size: 0.8rem;
            text-transform: uppercase;
            color: var(--text-secondary);
            font-weight: 600;
            letter-spacing: 0.5px;
        }
        td { padding: 16px 20px; border-bottom: 1px solid var(--border-color); font-size: 0.95rem; }
        tr:hover { background-color: rgba(255,255,255,0.02); }

        .rank-cell { font-weight: 800; color: var(--text-secondary); width: 50px; }
        .bettor-name { font-weight: 600; color: #fff; }
        
        .val-pos { color: var(--accent-green); font-weight: 700; }
        .val-neg { color: var(--accent-red); font-weight: 700; }
        .val-neutral { color: var(--text-secondary); }

        .streak-w { color: var(--accent-green); font-weight: 700; }
        .streak-l { color: var(--accent-red); font-weight: 700; }

    </style>
</head>
<body>
    <div class="container">
        
        <header>
            <h1>American Betting League</h1>
            <div class="subtitle">Midseason Report</div>
            <div class="date-badge">📅 {{ date_str }}</div>
        </header>

        <!-- TOP & STEADY PERFORMERS -->
        <div class="grid-2">
            <!-- TOP PERFORMERS (UNITS) -->
            <div>
                <div class="section-title">
                    <span>Top Performers (Units)</span>
                </div>
                <div class="card">
                    <ul class="performer-list">
                        {% for p in top_performers %}
                        <li class="performer-item">
                            <div class="p-rank">#{{ p.RANK }}</div>
                            <div class="p-info">
                                <span class="p-name">{{ p.BETTOR }} <span class="badge-top">Top Earner</span></span>
                                <div class="p-sub">Record: {{ p.W }}-{{ p.L }}-{{ p.P }}</div>
                            </div>
                            <div class="p-stat">
                                <span class="p-val val-pos">+{{ "%.2f"|format(p.UNIT) }}u</span>
                                <span class="p-lbl">Profit</span>
                            </div>
                        </li>
                        {% endfor %}
                    </ul>
                </div>
            </div>

            <!-- TOP BETTOR FROM PREVIOUS DAY -->
            <div>
                 <div class="section-title" style="border-color: var(--accent-green);">
                    <span>Top Bettor From Yesterday</span>
                </div>
                <div class="card">
                    <ul class="performer-list">
                        {% for p in yesterday_top %}
                        <li class="performer-item">
                            <div class="p-rank">#{{ p.RANK }}</div>
                            <div class="p-info">
                                <span class="p-name">{{ p.BETTOR }} <span class="badge-top">Hot 🔥</span></span>
                                <div class="p-sub">Record: {{ p.W }}-{{ p.L }}-{{ p.P }}</div>
                            </div>
                            <div class="p-stat">
                                <span class="p-val val-pos">{{ "%+.2f"|format(p['LDAY UNITS']) }}u</span>
                                <span class="p-lbl">Yesterday</span>
                            </div>
                        </li>
                        {% endfor %}
                    </ul>
                </div>
            </div>
        </div>

        <!-- BAR GRAPH -->
        <div class="section-title">
            <span>League Leaders (Top 10 Units)</span>
        </div>
        <div class="card" style="margin-bottom: 50px;">
            {{ bar_chart|safe }}
        </div>

        <!-- FULL STANDINGS -->
        <div class="section-title">
            <span>Official Standings</span>
        </div>
        <div class="standings-container">
            <table>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Bettor</th>
                        <th>Total Units</th>
                        <th>Record</th>
                        <th>Win %</th>
                        <th>Yesterday</th>
                        <th>Streak</th>
                    </tr>
                </thead>
                <tbody>
                    {% for row in data %}
                    <tr>
                        <td class="rank-cell">{{ row.RANK }}</td>
                        <td class="bettor-name">{{ row.BETTOR }}</td>
                        <td class="{{ 'val-pos' if row.UNIT > 0 else 'val-neutral' if row.UNIT == 0 else 'val-neg' }}">
                            {{ "%.2f"|format(row.UNIT) }}
                        </td>
                        <td style="color: var(--text-secondary);">
                            {{ row.W }}-{{ row.L }}-{{ row.P }}
                        </td>
                        <td>{{ row['%'] }}</td>
                        <td>
                            {% if row['LDAY UNITS'] != 0 %}
                            <span class="{{ 'val-pos' if row['LDAY UNITS'] > 0 else 'val-neg' }}">
                                {{ "%.2f"|format(row['LDAY UNITS']) }}u
                            </span>
                            {% else %}
                            <span class="val-neutral">-</span>
                            {% endif %}
                        </td>
                        <td>
                            {% if 'W' in row.STRK %}
                            <span class="streak-w">{{ row.STRK }}</span>
                            {% elif 'L' in row.STRK %}
                            <span class="streak-l">{{ row.STRK }}</span>
                            {% else %}
                            <span style="color: grey;">{{ row.STRK }}</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

    </div>
</body>
</html>
"""

def clean_dataframe(df):
    """Cleans numeric columns from strings with symbols to pure floats."""
    cols_to_clean = ['UNIT', 'RANK', 'LDAY UNITS', 'W', 'L', 'P']
    for col in cols_to_clean:
        if col in df.columns:
            df[col] = df[col].astype(str).replace(r'[^\d.-]', '', regex=True)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

def generate_bar_chart(df, top_n=10):
    """Generates a Plotly Bar Chart for the Top N bettors by Units."""
    # Filter only positive units for the chart to look nice, or just take top N regardless
    top_df = df.sort_values('UNIT', ascending=False).head(top_n).copy()
    
    # Color logic: Green for > 0, Red for < 0
    top_df['Color'] = top_df['UNIT'].apply(lambda x: '#228B22' if x >= 0 else '#f87171')

    fig = px.bar(
        top_df, 
        x='BETTOR', 
        y='UNIT',
        text_auto='.2f',
        title=None
    )
    
    fig.update_traces(
        marker_color=top_df['Color'],
        textfont_size=12,
        textfont_color='white',
        textposition='outside',
        cliponaxis=False 
    )

    fig.update_layout(
        paper_bgcolor='#1e1e1e',
        plot_bgcolor='#1e1e1e',
        font={'family': 'Inter', 'color': '#b3b3b3'},
        xaxis=dict(
            showgrid=False, 
            linecolor='#333',
            tickangle=0,
            title=None,
            tickfont=dict(size=11, color='#fff')
        ),
        yaxis=dict(
            showgrid=True, 
            gridcolor='#2a2a2a', 
            zerolinecolor='#333',
            title='Total Units'
        ),
        margin=dict(l=20, r=20, t=20, b=40),
        height=400,
        showlegend=False
    )
    
    return pio.to_html(fig, include_plotlyjs='cdn', full_html=False)

def helper_parse_percent(val):
    """Converts '52%' string to 52.0 float."""
    try:
        if isinstance(val, str):
            return float(val.replace('%', ''))
        return float(val)
    except:
        return 0.0

def create_dashboard():
    print("=" * 60)
    print("ABL AUTOMATED DASHBOARD GENERATOR")
    print("=" * 60)
    
    ssl._create_default_https_context = ssl._create_unverified_context
    os.makedirs(HISTORY_FOLDER, exist_ok=True)

    # 1. Fetch Data (Directly from Sheet for Automation)
    print("Fetching latest data from Google Sheets...")
    try:
        df_current = pd.read_csv(SHEET_URL)
        df_current = clean_dataframe(df_current)
        
        # Save history
        today_str = datetime.now().strftime("%Y-%m-%d")
        df_current.to_csv(os.path.join(HISTORY_FOLDER, f"{today_str}.csv"), index=False)
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        return

    # 2. Logic: Top Performers (Units)
    top_performers = df_current[df_current['UNIT'] > 0].sort_values('UNIT', ascending=False).head(5)
    
    # 3. Logic: Consistent/Steady (Win %)
    df_current['total_bets'] = df_current['W'] + df_current['L']
    qualified_df = df_current[df_current['total_bets'] >= 15].copy()
    
    if qualified_df.empty:
        qualified_df = df_current.head(10).copy()

    # Get top performers from yesterday (LDAY UNITS)
    yesterday_top = df_current[df_current['LDAY UNITS'] > 0].sort_values('LDAY UNITS', ascending=False).head(5)

    # 4. Bar Graph
    bar_html = generate_bar_chart(df_current, top_n=10)

    # 5. Render HTML
    print("Rendering Dashboard...")
    env = jinja2.Environment(loader=jinja2.BaseLoader())
    html = env.from_string(HTML_TEMPLATE).render(
        data=df_current.to_dict('records'),
        top_performers=top_performers.to_dict('records'),
        yesterday_top=yesterday_top.to_dict('records'),
        bar_chart=bar_html,
        date_str=datetime.now().strftime("%B %d, %Y")
    )

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"SUCCESS! Automated Dashboard generated: {os.path.abspath(OUTPUT_FILE)}")

if __name__ == "__main__":
    create_dashboard()