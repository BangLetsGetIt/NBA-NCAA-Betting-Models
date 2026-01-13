#!/usr/bin/env python3
"""
Sports Models Analytics Dashboard Generator
Creates comprehensive HTML dashboard with charts and analytical breakdowns
"""

import json
import os
import glob
from datetime import datetime, timedelta
from collections import defaultdict, Counter

class AnalyticsDashboard:
    def __init__(self, base_dir="/Users/rico/sports-models"):
        self.base_dir = base_dir
        self.tracking_files = []
        self.all_data = {}
        self.load_tracking_files()
    
    def load_tracking_files(self):
        """Load all tracking JSON files"""
        patterns = [
            "nba/*tracking.json",
            "nfl/*tracking.json", 
            "ncaa/*tracking.json",
            "wnba/*tracking.json",
            "soccer/*tracking.json",
            "mlb/*tracking.json",
            "*tracking.json"
        ]
        
        for pattern in patterns:
            files = glob.glob(os.path.join(self.base_dir, pattern))
            # Skip backup files
            files = [f for f in files if "tools/reports/backups" not in f]
            self.tracking_files.extend(files)
        
        print(f"Found {len(self.tracking_files)} tracking files")
    
    def load_data(self):
        """Load and parse all tracking data"""
        for file_path in self.tracking_files:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if 'picks' in data and data['picks']:
                        self.all_data[file_path] = data
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
    
    def get_sport_from_filename(self, filepath):
        """Extract sport type from filename"""
        if 'nba' in filepath.lower():
            return 'NBA'
        elif 'nfl' in filepath.lower():
            return 'NFL'
        elif 'ncaa' in filepath.lower() or 'cbb' in filepath.lower():
            return 'NCAAB'
        elif 'wnba' in filepath.lower():
            return 'WNBA'
        elif 'soccer' in filepath.lower():
            return 'Soccer'
        elif 'mlb' in filepath.lower():
            return 'MLB'
        else:
            return 'Other'
    
    def get_model_type(self, filepath):
        """Extract model type from filename"""
        filename = os.path.basename(filepath)
        if 'props' in filename.lower():
            if 'points' in filename.lower():
                return 'Points Props'
            elif 'rebounds' in filename.lower():
                return 'Rebounds Props'
            elif 'assists' in filename.lower():
                return 'Assists Props'
            elif '3pt' in filename.lower():
                return '3PT Props'
            elif 'passing' in filename.lower():
                return 'Passing Yards Props'
            elif 'rushing' in filename.lower():
                return 'Rushing Yards Props'
            elif 'receiving' in filename.lower():
                return 'Receiving Yards Props'
            elif 'receptions' in filename.lower():
                return 'Receptions Props'
            elif 'atd' in filename.lower():
                return 'ATD Props'
            else:
                return 'Props'
        elif 'best_plays' in filename.lower():
            return 'Best Plays'
        else:
            return 'Main Model'
    
    def calculate_metrics(self, picks):
        """Calculate performance metrics for a set of picks"""
        if not picks:
            return {
                'total_picks': 0,
                'wins': 0,
                'losses': 0,
                'pushes': 0,
                'win_rate': 0.0,
                'profit_loss': 0.0,
                'roi': 0.0,
                'avg_edge': 0.0,
                'avg_ai_score': 0.0
            }
        
        total_picks = len(picks)
        wins = sum(1 for p in picks if p.get('status') == 'win')
        losses = sum(1 for p in picks if p.get('status') == 'loss')
        pushes = sum(1 for p in picks if p.get('status') == 'push')
        win_rate = wins / total_picks if total_picks > 0 else 0
        
        # Calculate profit/loss
        profit_loss = sum(p.get('profit_loss', 0) if p.get('profit_loss') is not None else 0 for p in picks)
        
        # Calculate ROI (assuming $1 per bet)
        total_bet = total_picks * 1.0
        roi = (profit_loss / total_bet * 100) if total_bet > 0 else 0
        
        # Calculate averages
        edges = [p.get('edge', 0) for p in picks if p.get('edge') is not None]
        avg_edge = sum(edges) / len(edges) if edges else 0
        
        ai_scores = [p.get('ai_score', 0) for p in picks if p.get('ai_score') is not None]
        avg_ai_score = sum(ai_scores) / len(ai_scores) if ai_scores else 0
        
        return {
            'total_picks': total_picks,
            'wins': wins,
            'losses': losses,
            'pushes': pushes,
            'win_rate': win_rate,
            'profit_loss': profit_loss,
            'roi': roi,
            'avg_edge': avg_edge,
            'avg_ai_score': avg_ai_score
        }
    
    def generate_analytics(self):
        """Generate comprehensive analytics"""
        analytics = {
            'overview': {},
            'by_sport': defaultdict(dict),
            'by_model_type': defaultdict(dict),
            'time_series': {},
            'top_performers': {},
            'edge_analysis': {},
            'ai_score_analysis': {}
        }
        
        all_picks = []
        sport_picks = defaultdict(list)
        model_type_picks = defaultdict(list)
        
        # Aggregate all picks
        for filepath, data in self.all_data.items():
            sport = self.get_sport_from_filename(filepath)
            model_type = self.get_model_type(filepath)
            
            for pick in data['picks']:
                pick['sport'] = sport
                pick['model_type'] = model_type
                pick['filepath'] = filepath
                
                all_picks.append(pick)
                sport_picks[sport].append(pick)
                model_type_picks[model_type].append(pick)
        
        # Overall metrics
        analytics['overview'] = self.calculate_metrics(all_picks)
        
        # By sport
        for sport, picks in sport_picks.items():
            analytics['by_sport'][sport] = self.calculate_metrics(picks)
        
        # By model type
        for model_type, picks in model_type_picks.items():
            analytics['by_model_type'][model_type] = self.calculate_metrics(picks)
        
        # Time series data (last 30 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        for pick in all_picks:
            if pick.get('game_time'):
                try:
                    game_date = datetime.fromisoformat(pick['game_time'].replace('Z', '+00:00')).date()
                    if start_date.date() <= game_date <= end_date.date():
                        date_str = game_date.strftime('%Y-%m-%d')
                        daily_picks = [p for p in all_picks if p.get('game_time') and 
                                     datetime.fromisoformat(p['game_time'].replace('Z', '+00:00')).date() == game_date]
                        daily_metrics = self.calculate_metrics(daily_picks)
                        daily_metrics_copy = daily_metrics.copy()
                        daily_metrics_copy['date'] = date_str
                        analytics['time_series'][date_str] = daily_metrics_copy
                except:
                    continue
        
        # Top performers (players/teams with most wins)
        player_stats = defaultdict(dict)
        team_stats = defaultdict(dict)
        
        for pick in all_picks:
            if pick.get('status') in ['win', 'loss', 'push']:
                # Player stats (for props)
                if pick.get('player'):
                    player = pick['player']
                    if player not in player_stats:
                        player_stats[player] = {'wins': 0, 'losses': 0, 'pushes': 0, 'picks': []}
                    
                    if pick['status'] == 'win':
                        player_stats[player]['wins'] += 1
                    elif pick['status'] == 'loss':
                        player_stats[player]['losses'] += 1
                    else:
                        player_stats[player]['pushes'] += 1
                    player_stats[player]['picks'].append(pick)
                
                # Team stats (for main models)
                if pick.get('team'):
                    team = pick['team']
                    if team not in team_stats:
                        team_stats[team] = {'wins': 0, 'losses': 0, 'pushes': 0, 'picks': []}
                    
                    if pick['status'] == 'win':
                        team_stats[team]['wins'] += 1
                    elif pick['status'] == 'loss':
                        team_stats[team]['losses'] += 1
                    else:
                        team_stats[team]['pushes'] += 1
                    team_stats[team]['picks'].append(pick)
        
        # Calculate win rates and get top performers
        for player, stats in player_stats.items():
            wins = stats['wins']
            losses = stats['losses']
            total = wins + losses
            if total >= 5:  # Minimum 5 picks
                win_rate = wins / total
                analytics['top_performers'][f"player_{player}"] = {
                    'name': player,
                    'type': 'player',
                    'wins': wins,
                    'losses': losses,
                    'pushes': stats['pushes'],
                    'win_rate': win_rate,
                    'total_picks': total
                }
        
        for team, stats in team_stats.items():
            wins = stats['wins']
            losses = stats['losses']
            total = wins + losses
            if total >= 3:  # Minimum 3 picks
                win_rate = wins / total
                analytics['top_performers'][f"team_{team}"] = {
                    'name': team,
                    'type': 'team',
                    'wins': wins,
                    'losses': losses,
                    'pushes': stats['pushes'],
                    'win_rate': win_rate,
                    'total_picks': total
                }
        
        # Sort top performers by win rate
        analytics['top_performers'] = dict(
            sorted(analytics['top_performers'].items(), 
                   key=lambda x: x[1]['win_rate'], reverse=True)[:20]
        )
        
        # Edge distribution analysis
        edges = [p.get('edge', 0) for p in all_picks if p.get('edge') is not None]
        if edges:
            analytics['edge_analysis'] = {
                'avg_edge': sum(edges) / len(edges),
                'median_edge': sorted(edges)[len(edges) // 2],
                'max_edge': max(edges),
                'min_edge': min(edges),
                'edge_ranges': {
                    'negative': len([e for e in edges if e < 0]),
                    '0-5': len([e for e in edges if 0 <= e < 5]),
                    '5-10': len([e for e in edges if 5 <= e < 10]),
                    '10-15': len([e for e in edges if 10 <= e < 15]),
                    '15+': len([e for e in edges if e >= 15])
                }
            }
        
        # AI score analysis
        ai_scores = [p.get('ai_score', 0) for p in all_picks if p.get('ai_score') is not None]
        if ai_scores:
            analytics['ai_score_analysis'] = {
                'avg_ai_score': sum(ai_scores) / len(ai_scores),
                'max_ai_score': max(ai_scores),
                'min_ai_score': min(ai_scores),
                'score_distribution': {
                    '0-2': len([s for s in ai_scores if 0 <= s < 2]),
                    '2-4': len([s for s in ai_scores if 2 <= s < 4]),
                    '4-6': len([s for s in ai_scores if 4 <= s < 6]),
                    '6-8': len([s for s in ai_scores if 6 <= s < 8]),
                    '8-10': len([s for s in ai_scores if 8 <= s <= 10])
                }
            }
        
        return analytics
    
    def generate_html(self, analytics):
        """Generate HTML dashboard"""
        
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sports Models Analytics Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: #333;
            min-height: 100vh;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .header { 
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        .header h1 { 
            color: #1e3c72;
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 700;
        }
        .header p { color: #666; font-size: 1.1em; }
        .overview-grid { 
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .metric-card { 
            background: rgba(255, 255, 255, 0.95);
            border-radius: 12px;
            padding: 25px;
            text-align: center;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        .metric-card:hover { transform: translateY(-5px); }
        .metric-value { 
            font-size: 2.2em;
            font-weight: 700;
            margin-bottom: 8px;
        }
        .metric-label { 
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .positive { color: #28a745; }
        .negative { color: #dc3545; }
        .neutral { color: #6c757d; }
        .section { 
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        .section h2 { 
            color: #1e3c72;
            margin-bottom: 20px;
            font-size: 1.8em;
            border-bottom: 3px solid #1e3c72;
            padding-bottom: 10px;
        }
        .chart-container { 
            position: relative;
            height: 400px;
            margin: 20px 0;
        }
        .table { 
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        .table th, .table td { 
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        .table th { 
            background: #1e3c72;
            color: white;
            font-weight: 600;
        }
        .table tr:hover { background: #f8f9fa; }
        .grid { 
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 30px;
        }
        .badge { 
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: 600;
        }
        .badge-nba { background: #FF6B35; color: white; }
        .badge-nfl { background: #2E7D32; color: white; }
        .badge-ncaab { background: #1976D2; color: white; }
        .badge-wnba { background: #E91E63; color: white; }
        .badge-soccer { background: #4CAF50; color: white; }
        .badge-mlb { background: #F44336; color: white; }
        .footer { 
            text-align: center;
            padding: 20px;
            color: rgba(255,255,255,0.8);
            font-size: 0.9em;
        }
        @media (max-width: 768px) {
            .container { padding: 10px; }
            .header h1 { font-size: 2em; }
            .overview-grid { grid-template-columns: repeat(2, 1fr); }
            .grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Sports Models Analytics Dashboard</h1>
            <p>Complete Performance Analysis & Tracking</p>
            <p><small>Last Updated: {{ timestamp }}</small></p>
        </div>

        <!-- Overview Metrics -->
        <div class="overview-grid">
            <div class="metric-card">
                <div class="metric-value {{ 'positive' if analytics.overview.profit_loss > 0 else 'negative' if analytics.overview.profit_loss < 0 else 'neutral' }}">
                    ${{ "%.2f"|format(analytics.overview.profit_loss) }}
                </div>
                <div class="metric-label">Total P&L</div>
            </div>
            <div class="metric-card">
                <div class="metric-value {{ 'positive' if analytics.overview.roi > 0 else 'negative' if analytics.overview.roi < 0 else 'neutral' }}">
                    {{ "%.1f"|format(analytics.overview.roi) }}%
                </div>
                <div class="metric-label">ROI</div>
            </div>
            <div class="metric-card">
                <div class="metric-value {{ 'positive' if analytics.overview.win_rate > 0.5 else 'negative' }}">
                    {{ "%.1f"|format(analytics.overview.win_rate * 100) }}%
                </div>
                <div class="metric-label">Win Rate</div>
            </div>
            <div class="metric-card">
                <div class="metric-value neutral">
                    {{ analytics.overview.total_picks }}
                </div>
                <div class="metric-label">Total Picks</div>
            </div>
        </div>

        <!-- Performance by Sport -->
        <div class="section">
            <h2>🏈 Performance by Sport</h2>
            <div class="chart-container">
                <canvas id="sportChart"></canvas>
            </div>
            <table class="table">
                <thead>
                    <tr>
                        <th>Sport</th>
                        <th>Picks</th>
                        <th>Win Rate</th>
                        <th>P&L</th>
                        <th>ROI</th>
                        <th>Avg Edge</th>
                    </tr>
                </thead>
                <tbody>
                    {% for sport, metrics in analytics.by_sport.items() %}
                    <tr>
                        <td>
                            <span class="badge badge-{{ sport.lower() }}">{{ sport }}</span>
                        </td>
                        <td>{{ metrics.total_picks }}</td>
                        <td>{{ "%.1f"|format(metrics.win_rate * 100) }}%</td>
                        <td class="{{ 'positive' if metrics.profit_loss > 0 else 'negative' if metrics.profit_loss < 0 else 'neutral' }}">
                            ${{ "%.2f"|format(metrics.profit_loss) }}
                        </td>
                        <td class="{{ 'positive' if metrics.roi > 0 else 'negative' if metrics.roi < 0 else 'neutral' }}">
                            {{ "%.1f"|format(metrics.roi) }}%
                        </td>
                        <td>{{ "%.1f"|format(metrics.avg_edge) }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <!-- Model Type Performance -->
        <div class="section">
            <h2>🤖 Model Type Performance</h2>
            <div class="chart-container">
                <canvas id="modelChart"></canvas>
            </div>
        </div>

        <!-- Time Series Performance -->
        <div class="section">
            <h2>📈 30-Day Performance Trend</h2>
            <div class="chart-container">
                <canvas id="trendChart"></canvas>
            </div>
        </div>

        <!-- Top Performers -->
        <div class="section">
            <h2>🏆 Top Performers</h2>
            <div class="grid">
                <div>
                    <h3>Players</h3>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Player</th>
                                <th>Picks</th>
                                <th>Win Rate</th>
                                <th>Record</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for key, performer in analytics.top_performers.items() %}
                            {% if performer.type == 'player' %}
                            <tr>
                                <td>{{ performer.name }}</td>
                                <td>{{ performer.total_picks }}</td>
                                <td class="{{ 'positive' if performer.win_rate > 0.6 else 'neutral' }}">
                                    {{ "%.1f"|format(performer.win_rate * 100) }}%
                                </td>
                                <td>{{ performer.wins }}-{{ performer.losses }}-{{ performer.pushes }}</td>
                            </tr>
                            {% endif %}
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                <div>
                    <h3>Teams</h3>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Team</th>
                                <th>Picks</th>
                                <th>Win Rate</th>
                                <th>Record</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for key, performer in analytics.top_performers.items() %}
                            {% if performer.type == 'team' %}
                            <tr>
                                <td>{{ performer.name }}</td>
                                <td>{{ performer.total_picks }}</td>
                                <td class="{{ 'positive' if performer.win_rate > 0.6 else 'neutral' }}">
                                    {{ "%.1f"|format(performer.win_rate * 100) }}%
                                </td>
                                <td>{{ performer.wins }}-{{ performer.losses }}-{{ performer.pushes }}</td>
                            </tr>
                            {% endif %}
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Edge & AI Score Analysis -->
        <div class="section">
            <h2>📊 Edge & AI Score Analysis</h2>
            <div class="grid">
                <div>
                    <h3>Edge Distribution</h3>
                    <div class="chart-container" style="height: 300px;">
                        <canvas id="edgeChart"></canvas>
                    </div>
                    <p><strong>Average Edge:</strong> {{ "%.1f"|format(analytics.edge_analysis.avg_edge) }}</p>
                    <p><strong>Median Edge:</strong> {{ "%.1f"|format(analytics.edge_analysis.median_edge) }}</p>
                </div>
                <div>
                    <h3>AI Score Distribution</h3>
                    <div class="chart-container" style="height: 300px;">
                        <canvas id="aiScoreChart"></canvas>
                    </div>
                    <p><strong>Average AI Score:</strong> {{ "%.1f"|format(analytics.ai_score_analysis.avg_ai_score) }}</p>
                    <p><strong>Max AI Score:</strong> {{ analytics.ai_score_analysis.max_ai_score }}</p>
                </div>
            </div>
        </div>

        <div class="footer">
            <p>Generated by Sports Models Analytics Dashboard | Data from {{ analytics.overview.total_picks }} total picks</p>
        </div>
    </div>

    <script>
        // Chart.js configurations
        const chartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                }
            }
        };

        // Sport Performance Chart
        const sportCtx = document.getElementById('sportChart').getContext('2d');
        new Chart(sportCtx, {
            type: 'bar',
            data: {
                labels: [{% for sport in analytics.by_sport.keys() %}'{{ sport }}'{% if not loop.last %},{% endif %}{% endfor %}],
                datasets: [{
                    label: 'Win Rate %',
                    data: [{% for sport, metrics in analytics.by_sport.items() %}{{ "%.1f"|format(metrics.win_rate * 100) }}{% if not loop.last %},{% endif %}{% endfor %}],
                    backgroundColor: 'rgba(30, 60, 114, 0.8)',
                    borderColor: 'rgba(30, 60, 114, 1)',
                    borderWidth: 1
                }, {
                    label: 'ROI %',
                    data: [{% for sport, metrics in analytics.by_sport.items() %}{{ "%.1f"|format(metrics.roi) }}{% if not loop.last %},{% endif %}{% endfor %}],
                    backgroundColor: 'rgba(40, 167, 69, 0.8)',
                    borderColor: 'rgba(40, 167, 69, 1)',
                    borderWidth: 1
                }]
            },
            options: chartOptions
        });

        // Model Type Chart
        const modelCtx = document.getElementById('modelChart').getContext('2d');
        new Chart(modelCtx, {
            type: 'doughnut',
            data: {
                labels: [{% for model_type in analytics.by_model_type.keys() %}'{{ model_type }}'{% if not loop.last %},{% endif %}{% endfor %}],
                datasets: [{
                    data: [{% for model_type, metrics in analytics.by_model_type.items() %}{{ metrics.total_picks }}{% if not loop.last %},{% endif %}{% endfor %}],
                    backgroundColor: [
                        '#FF6B35', '#2E7D32', '#1976D2', '#E91E63',
                        '#4CAF50', '#F44336', '#9C27B0', '#FF9800'
                    ]
                }]
            },
            options: chartOptions
        });

        // Time Series Chart
        const trendCtx = document.getElementById('trendChart').getContext('2d');
        new Chart(trendCtx, {
            type: 'line',
            data: {
                labels: [{% for date in analytics.time_series.keys()|sort %}'{{ date }}'{% if not loop.last %},{% endif %}{% endfor %}],
                datasets: [{
                    label: 'Cumulative P&L ($)',
                    data: [{% for date in analytics.time_series.keys()|sort %}{{ "%.2f"|format(analytics.time_series[date].profit_loss) }}{% if not loop.last %},{% endif %}{% endfor %}],
                    borderColor: 'rgba(30, 60, 114, 1)',
                    backgroundColor: 'rgba(30, 60, 114, 0.1)',
                    tension: 0.4
                }, {
                    label: 'Win Rate %',
                    data: [{% for date in analytics.time_series.keys()|sort %}{{ "%.1f"|format(analytics.time_series[date].win_rate * 100) }}{% if not loop.last %},{% endif %}{% endfor %}],
                    borderColor: 'rgba(40, 167, 69, 1)',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    tension: 0.4,
                    yAxisID: 'y1'
                }]
            },
            options: {
                ...chartOptions,
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: {
                            drawOnChartArea: false,
                        },
                    }
                }
            }
        });

        // Edge Distribution Chart
        const edgeCtx = document.getElementById('edgeChart').getContext('2d');
        new Chart(edgeCtx, {
            type: 'bar',
            data: {
                labels: ['Negative', '0-5', '5-10', '10-15', '15+'],
                datasets: [{
                    label: 'Number of Picks',
                    data: [
                        {{ analytics.edge_analysis.edge_ranges.negative }},
                        {{ analytics.edge_analysis.edge_ranges['0-5'] }},
                        {{ analytics.edge_analysis.edge_ranges['5-10'] }},
                        {{ analytics.edge_analysis.edge_ranges['10-15'] }},
                        {{ analytics.edge_analysis.edge_ranges['15+'] }}
                    ],
                    backgroundColor: [
                        '#dc3545', '#6c757d', '#ffc107', '#28a745', '#007bff'
                    ]
                }]
            },
            options: chartOptions
        });

        // AI Score Distribution Chart
        const aiScoreCtx = document.getElementById('aiScoreChart').getContext('2d');
        new Chart(aiScoreCtx, {
            type: 'bar',
            data: {
                labels: ['0-2', '2-4', '4-6', '6-8', '8-10'],
                datasets: [{
                    label: 'Number of Picks',
                    data: [
                        {{ analytics.ai_score_analysis.score_distribution['0-2'] }},
                        {{ analytics.ai_score_analysis.score_distribution['2-4'] }},
                        {{ analytics.ai_score_analysis.score_distribution['4-6'] }},
                        {{ analytics.ai_score_analysis.score_distribution['6-8'] }},
                        {{ analytics.ai_score_analysis.score_distribution['8-10'] }}
                    ],
                    backgroundColor: [
                        '#dc3545', '#f8f9fa', '#ffc107', '#28a745', '#007bff'
                    ]
                }]
            },
            options: chartOptions
        });
    </script>
</body>
</html>
        """
        
        # Simple string formatting instead of Jinja2
        html_output = html_template.replace('{{ analytics.overview.total_picks }}', str(analytics['overview']['total_picks']))
        html_output = html_output.replace('{{ analytics.overview.profit_loss }}', f"{analytics['overview']['profit_loss']:.2f}")
        html_output = html_output.replace('{{ analytics.overview.roi }}', f"{analytics['overview']['roi']:.1f}")
        html_output = html_output.replace('{{ analytics.overview.win_rate }}', f"{analytics['overview']['win_rate']:.1f}")
        html_output = html_output.replace('{{ timestamp }}', datetime.now().strftime('%Y-%m-%d %H:%M:%S ET'))
        
        return html_output
    
    def run(self):
        """Main execution method"""
        print("🏈 Loading tracking data...")
        self.load_data()
        
        print("📊 Generating analytics...")
        analytics = self.generate_analytics()
        
        print("🎨 Creating HTML dashboard...")
        html_output = self.generate_html(analytics)
        
        output_path = os.path.join(self.base_dir, "analytics_dashboard.html")
        with open(output_path, 'w') as f:
            f.write(html_output)
        
        print(f"✅ Dashboard created: {output_path}")
        print(f"📈 Total picks analyzed: {analytics['overview']['total_picks']}")
        print(f"💰 Overall P&L: ${analytics['overview']['profit_loss']:.2f}")
        print(f"🎯 Win Rate: {analytics['overview']['win_rate']*100:.1f}%")
        
        return output_path, analytics

if __name__ == "__main__":
    dashboard = AnalyticsDashboard()
    dashboard.run()