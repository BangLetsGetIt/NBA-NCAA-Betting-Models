#!/usr/bin/env python3

import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

class SportsAnalytics:
    def __init__(self):
        self.base_dir = Path("/Users/rico/sports-models")
        self.all_picks = []
        self.tracking_files = [
            "nba/nba_picks_tracking.json",
            "nba/nba_points_props_tracking.json", 
            "nba/nba_rebounds_props_tracking.json",
            "nba/nba_assists_props_tracking.json",
            "nba/nba_3pt_props_tracking.json",
            "ncaa/ncaab_picks_tracking.json",
            "ncaa/cbb_rebounds_props_tracking.json",
            "soccer/soccer_picks_tracking.json",
            "wnba/wnba_model_tracking.json",
            "wnba/wnba_props_tracking.json",
            "best_plays_tracking.json"
        ]
        
    def load_all_tracking_data(self):
        """Load data from all tracking files"""
        for file_path in self.tracking_files:
            full_path = self.base_dir / file_path
            if full_path.exists():
                try:
                    with open(full_path, 'r') as f:
                        data = json.load(f)
                        # Handle both list format and dict with "picks" key
                        if isinstance(data, dict) and 'picks' in data:
                            picks = data['picks']
                        elif isinstance(data, list):
                            picks = data
                        else:
                            print(f"Unexpected format in {file_path}")
                            continue
                            
                        for pick in picks:
                            pick['sport'] = self.get_sport_from_file(file_path)
                            pick['model_type'] = self.get_model_type_from_file(file_path)
                        self.all_picks.extend(picks)
                except Exception as e:
                    print(f"Error loading {file_path}: {e}")
        
        print(f"Loaded {len(self.all_picks)} total picks")
        
    def get_sport_from_file(self, file_path):
        """Extract sport from file path"""
        if 'nba' in file_path:
            return 'NBA'
        elif 'nfl' in file_path:
            return 'NFL'
        elif 'ncaa' in file_path or 'cbb' in file_path:
            return 'NCAAB'
        elif 'soccer' in file_path:
            return 'Soccer'
        elif 'wnba' in file_path:
            return 'WNBA'
        elif 'mlb' in file_path:
            return 'MLB'
        else:
            return 'Other'
            
    def get_model_type_from_file(self, file_path):
        """Extract model type from file path"""
        if 'props' in file_path:
            return 'Props'
        elif 'atd' in file_path:
            return 'ATD'
        elif 'main' in file_path or file_path.endswith('_picks_tracking.json'):
            return 'Main'
        else:
            return 'Other'
    
    def calculate_overview_metrics(self):
        """Calculate overall metrics"""
        total_picks = len(self.all_picks)
        if total_picks == 0:
            return self.empty_metrics()
            
        completed_picks = [p for p in self.all_picks if p.get('status') in ['win', 'loss', 'push']]
        wins = len([p for p in completed_picks if p.get('status') == 'win'])
        losses = len([p for p in completed_picks if p.get('status') == 'loss'])
        pushes = len([p for p in completed_picks if p.get('status') == 'push'])
        
        total_profit_loss = sum(p.get('profit_loss', 0) for p in completed_picks)
        total_bet_amount = len(completed_picks) * 100  # Assuming $100 per bet
        
        win_rate = wins / len(completed_picks) if completed_picks else 0
        roi = (total_profit_loss / total_bet_amount * 100) if total_bet_amount > 0 else 0
        
        return {
            'total_picks': total_picks,
            'completed_picks': len(completed_picks),
            'wins': wins,
            'losses': losses, 
            'pushes': pushes,
            'win_rate': win_rate,
            'profit_loss': total_profit_loss / 100,  # Convert cents to units
            'roi': roi
        }
    
    def calculate_by_sport(self):
        """Calculate metrics broken down by sport"""
        sport_metrics = {}
        
        for sport in ['NBA', 'NCAAB', 'Soccer', 'WNBA', 'MLB']:
            sport_picks = [p for p in self.all_picks if p.get('sport') == sport]
            if not sport_picks:
                continue
                
            completed_picks = [p for p in sport_picks if p.get('status') in ['win', 'loss', 'push']]
            if not completed_picks:
                continue
                
            wins = len([p for p in completed_picks if p.get('status') == 'win'])
            losses = len([p for p in completed_picks if p.get('status') == 'loss'])
            pushes = len([p for p in completed_picks if p.get('status') == 'push'])
            
            total_profit_loss = sum(p.get('profit_loss', 0) for p in completed_picks)
            total_bet_amount = len(completed_picks) * 100
            
            win_rate = wins / len(completed_picks)
            roi = (total_profit_loss / total_bet_amount * 100) if total_bet_amount > 0 else 0
            avg_edge = sum(p.get('edge', 0) for p in sport_picks) / len(sport_picks) if sport_picks else 0
            
            sport_metrics[sport] = {
                'total_picks': len(sport_picks),
                'completed_picks': len(completed_picks),
                'wins': wins,
                'losses': losses,
                'pushes': pushes,
                'win_rate': win_rate,
                'profit_loss': total_profit_loss / 100,
                'roi': roi,
                'avg_edge': avg_edge
            }
            
        return sport_metrics
    
    def calculate_by_model_type(self):
        """Calculate metrics broken down by model type"""
        model_metrics = {}
        
        for model_type in ['Main', 'Props', 'ATD']:
            model_picks = [p for p in self.all_picks if p.get('model_type') == model_type]
            if not model_picks:
                continue
                
            completed_picks = [p for p in model_picks if p.get('status') in ['win', 'loss', 'push']]
            if not completed_picks:
                continue
                
            wins = len([p for p in completed_picks if p.get('status') == 'win'])
            losses = len([p for p in completed_picks if p.get('status') == 'loss'])
            pushes = len([p for p in completed_picks if p.get('status') == 'push'])
            
            total_profit_loss = sum(p.get('profit_loss', 0) for p in completed_picks)
            total_bet_amount = len(completed_picks) * 100
            
            win_rate = wins / len(completed_picks)
            roi = (total_profit_loss / total_bet_amount * 100) if total_bet_amount > 0 else 0
            
            model_metrics[model_type] = {
                'total_picks': len(model_picks),
                'completed_picks': len(completed_picks),
                'wins': wins,
                'losses': losses,
                'pushes': pushes,
                'win_rate': win_rate,
                'profit_loss': total_profit_loss / 100,
                'roi': roi
            }
            
        return model_metrics
    
    def calculate_time_series(self):
        """Calculate time series data for all time"""
        time_series = {}
        
        # Find earliest and latest dates in the data
        all_dates = []
        for pick in self.all_picks:
            game_date = pick.get('game_date', '')
            if game_date:
                try:
                    if 'T' in game_date:
                        pick_date = datetime.fromisoformat(game_date.replace('Z', '+00:00')).strftime('%Y-%m-%d')
                    else:
                        pick_date = game_date
                    all_dates.append(pick_date)
                except:
                    pass
            elif pick.get('date'):
                all_dates.append(pick.get('date'))
        
        if not all_dates:
            return {}
        
        start_date = datetime.strptime(min(all_dates), '%Y-%m-%d')
        end_date = datetime.now()
        
        # Initialize all dates with empty metrics
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            time_series[date_str] = {
                'picks': 0,
                'wins': 0,
                'losses': 0,
                'pushes': 0,
                'profit_loss': 0,
                'win_rate': 0
            }
            current_date += timedelta(days=1)
        
        # Aggregate picks by date - check both game_date and date fields
        cumulative_profit_loss = 0
        cumulative_wins = 0
        cumulative_losses = 0
        cumulative_pushes = 0
        cumulative_completed = 0
        
        for date_str in sorted(time_series.keys()):
            date_picks = []
            for pick in self.all_picks:
                # Check game_date field (parse from ISO format)
                game_date = pick.get('game_date', '')
                if game_date:
                    try:
                        if 'T' in game_date:
                            pick_date = datetime.fromisoformat(game_date.replace('Z', '+00:00')).strftime('%Y-%m-%d')
                        else:
                            pick_date = game_date
                        if pick_date == date_str:
                            date_picks.append(pick)
                    except:
                        pass
                        
                # Also check date field if it exists
                elif pick.get('date') == date_str:
                    date_picks.append(pick)
                    
            completed_picks = [p for p in date_picks if p.get('status') in ['win', 'loss', 'push']]
            
            daily_wins = len([p for p in completed_picks if p.get('status') == 'win'])
            daily_losses = len([p for p in completed_picks if p.get('status') == 'loss'])
            daily_pushes = len([p for p in completed_picks if p.get('status') == 'push'])
            daily_profit_loss = sum(float(p.get('profit_loss', 0)) for p in completed_picks)
            
            cumulative_wins += daily_wins
            cumulative_losses += daily_losses
            cumulative_pushes += daily_pushes
            cumulative_completed += len(completed_picks)
            cumulative_profit_loss += daily_profit_loss
            
            time_series[date_str] = {
                'picks': len(date_picks),
                'wins': cumulative_wins,
                'losses': cumulative_losses,
                'pushes': cumulative_pushes,
                'profit_loss': cumulative_profit_loss / 100,
                'win_rate': cumulative_wins / cumulative_completed if cumulative_completed > 0 else 0
            }
            
        return time_series
    
    def calculate_top_performers(self):
        """Calculate top performing players and teams"""
# NBA team abbreviation mapping
        nba_team_mapping = {
            'Atlanta Hawks': 'atl', 'Boston Celtics': 'bos', 'Brooklyn Nets': 'bkn',
            'Charlotte Hornets': 'cha', 'Chicago Bulls': 'chi', 'Cleveland Cavaliers': 'cle',
            'Dallas Mavericks': 'dal', 'Denver Nuggets': 'den', 'Detroit Pistons': 'det',
            'Golden State Warriors': 'gsw', 'Houston Rockets': 'hou', 'Indiana Pacers': 'ind',
            'LA Clippers': 'lac', 'Los Angeles Lakers': 'lal', 'Memphis Grizzlies': 'mem',
            'Miami Heat': 'mia', 'Milwaukee Bucks': 'mil', 'Minnesota Timberwolves': 'min',
            'New Orleans Pelicans': 'no', 'New York Knicks': 'ny', 'Oklahoma City Thunder': 'okc',
            'Orlando Magic': 'orl', 'Philadelphia 76ers': 'phi', 'Phoenix Suns': 'phx',
            'Portland Trail Blazers': 'por', 'Sacramento Kings': 'sac', 'San Antonio Spurs': 'sa',
            'Toronto Raptors': 'tor', 'Utah Jazz': 'utah', 'Washington Wizards': 'was'
        }
        
        player_stats = defaultdict(lambda: {'picks': 0, 'wins': 0, 'losses': 0, 'pushes': 0, 'profit_loss': 0.0, 'sport': '', 'team': ''})
        team_stats = defaultdict(lambda: {'picks': 0, 'wins': 0, 'losses': 0, 'pushes': 0})
        
        for pick in self.all_picks:
            if pick.get('status') not in ['win', 'loss', 'push']:
                continue
                
            # Player stats
            player = pick.get('player')
            if player:
                player_stats[player]['picks'] = int(player_stats[player]['picks']) + 1
                player_stats[player]['sport'] = pick.get('sport', '')
                player_stats[player]['profit_loss'] = float(player_stats[player]['profit_loss']) + float(pick.get('profit_loss', 0))
                # Store team information (use home team)
                team = pick.get('home_team') or pick.get('team') or pick.get('away_team')
                if team and not player_stats[player]['team']:  # Only set once
                    player_stats[player]['team'] = team
                if pick.get('status') == 'win':
                    player_stats[player]['wins'] = int(player_stats[player]['wins']) + 1
                elif pick.get('status') == 'loss':
                    player_stats[player]['losses'] = int(player_stats[player]['losses']) + 1
                else:
                    player_stats[player]['pushes'] = int(player_stats[player]['pushes']) + 1
            
            # Team stats
            team = pick.get('team')
            if team:
                team_stats[team]['picks'] = int(team_stats[team]['picks']) + 1
                if pick.get('status') == 'win':
                    team_stats[team]['wins'] = int(team_stats[team]['wins']) + 1
                elif pick.get('status') == 'loss':
                    team_stats[team]['losses'] = int(team_stats[team]['losses']) + 1
                else:
                    team_stats[team]['pushes'] = int(team_stats[team]['pushes']) + 1
        
        # Convert to sorted lists
        top_players = []
        for player, stats in player_stats.items():
            if int(stats['picks']) >= 5:  # Minimum 5 picks
                total_completed = int(stats['wins']) + int(stats['losses']) + int(stats['pushes'])
                win_rate = int(stats['wins']) / total_completed if total_completed > 0 else 0
                
                # Get team abbreviation for logo
                team_name = stats['team']
                team_abbrev = ''
                if team_name in nba_team_mapping:
                    team_abbrev = nba_team_mapping[team_name]
                
                top_players.append({
                    'name': player,
                    'type': 'player',
                    'total_picks': int(stats['picks']),
                    'wins': int(stats['wins']),
                    'losses': int(stats['losses']),
                    'pushes': int(stats['pushes']),
                    'win_rate': win_rate,
                    'profit_loss': float(stats['profit_loss']) / 100,  # Convert cents to units
                    'sport': stats['sport'],
                    'team_abbrev': team_abbrev,
                    'team_name': team_name
                })
        
        top_teams = []
        for team, stats in team_stats.items():
            if int(stats['picks']) >= 5:  # Minimum 5 picks
                total_completed = int(stats['wins']) + int(stats['losses']) + int(stats['pushes'])
                win_rate = int(stats['wins']) / total_completed if total_completed > 0 else 0
                top_teams.append({
                    'name': team,
                    'type': 'team',
                    'total_picks': int(stats['picks']),
                    'wins': int(stats['wins']),
                    'losses': int(stats['losses']),
                    'pushes': int(stats['pushes']),
                    'win_rate': win_rate
                })
        
        # Sort by win rate and take top 10
        top_players.sort(key=lambda x: x['win_rate'], reverse=True)
        top_teams.sort(key=lambda x: x['win_rate'], reverse=True)
        
        # Combine into single dict
        top_performers = {}
        for i, player in enumerate(top_players[:15]):  # Increased to 15 for better selection
            top_performers[f'player_{i}'] = player
        for i, team in enumerate(top_teams[:10]):
            top_performers[f'team_{i}'] = team
            
        return top_performers

    def calculate_recent_performance(self, completed_picks, count):
        """Calculate recent performance for given number of picks"""
        if len(completed_picks) == 0:
            return {
                'wins': 0,
                'losses': 0,
                'pushes': 0,
                'win_rate': 0
            }
        
        # Sort by date_logged or game_date to get most recent first
        sorted_picks = sorted(completed_picks, 
                            key=lambda x: x.get('date_logged', x.get('game_date', '')), 
                            reverse=True)
        
        recent_picks = sorted_picks[:count]
        
        wins = len([p for p in recent_picks if p.get('status') == 'win'])
        losses = len([p for p in recent_picks if p.get('status') == 'loss'])
        pushes = len([p for p in recent_picks if p.get('status') == 'push'])
        total_completed = wins + losses + pushes
        
        win_rate = wins / total_completed if total_completed > 0 else 0
        
        return {
            'wins': wins,
            'losses': losses,
            'pushes': pushes,
            'win_rate': win_rate
        }

    def calculate_model_breakdown(self):
        """Calculate performance breakdown by individual models"""
        model_stats = {}
        
        # Map file paths to model names
        model_mapping = {
            'nba/nba_picks_tracking.json': 'NBA Main Model',
            'nba/nba_points_props_tracking.json': 'NBA Points Props',
            'nba/nba_rebounds_props_tracking.json': 'NBA Rebounds Props', 
            'nba/nba_assists_props_tracking.json': 'NBA Assists Props',
            'nba/nba_3pt_props_tracking.json': 'NBA 3PT Props',
            'ncaa/ncaab_picks_tracking.json': 'NCAAB Main Model',
            'ncaa/cbb_rebounds_props_tracking.json': 'NCAAB Rebounds Props',
            'soccer/soccer_picks_tracking.json': 'Soccer Model',
            'wnba/wnba_model_tracking.json': 'WNBA Main Model',
            'wnba/wnba_props_tracking.json': 'WNBA Props'
        }
        
        for file_path in self.tracking_files:
            full_path = self.base_dir / file_path
            if not full_path.exists():
                continue
                
            model_name = model_mapping.get(file_path, file_path.split('/')[-1].replace('.json', ''))
            
            try:
                with open(full_path, 'r') as f:
                    data = json.load(f)
                    
                    # Handle both list format and dict with "picks" key
                    if isinstance(data, dict) and 'picks' in data:
                        picks = data['picks']
                    elif isinstance(data, list):
                        picks = data
                    else:
                        continue
                        
                    completed_picks = [p for p in picks if p.get('status') in ['win', 'loss', 'push']]
                    if not completed_picks:
                        continue
                        
                    wins = len([p for p in completed_picks if p.get('status') == 'win'])
                    losses = len([p for p in completed_picks if p.get('status') == 'loss'])
                    pushes = len([p for p in completed_picks if p.get('status') == 'push'])
                    
                    total_profit_loss = sum(p.get('profit_loss', 0) for p in completed_picks)
                    win_rate = wins / len(completed_picks)
                    
                    # Calculate recent performance
                    recent_100 = self.calculate_recent_performance(completed_picks, 100)
                    recent_50 = self.calculate_recent_performance(completed_picks, 50)
                    recent_20 = self.calculate_recent_performance(completed_picks, 20)
                    recent_10 = self.calculate_recent_performance(completed_picks, 10)
                    
                    model_stats[model_name] = {
                        'total_picks': len(picks),
                        'completed_picks': len(completed_picks),
                        'wins': wins,
                        'losses': losses,
                        'pushes': pushes,
                        'win_rate': win_rate,
                        'profit_loss': total_profit_loss / 100,  # Convert cents to units
                        'roi': (total_profit_loss / (len(completed_picks) * 100) * 100) if completed_picks else 0,
                        'recent_100': recent_100,
                        'recent_50': recent_50,
                        'recent_20': recent_20,
                        'recent_10': recent_10
                    }
                    
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                continue
                
        # Filter and sort only NBA models by win rate
        nba_models = {}
        for model_name, metrics in model_stats.items():
            if 'NBA' in model_name:
                nba_models[model_name] = metrics
        
        # Sort by win rate (highest first)
        sorted_nba_models = dict(sorted(nba_models.items(), key=lambda x: x[1]['win_rate'], reverse=True))
        
        return sorted_nba_models
    
    def calculate_prop_breakdown(self):
        """Calculate performance by prop categories"""
        prop_stats = defaultdict(lambda: {'picks': 0, 'wins': 0, 'losses': 0, 'pushes': 0, 'profit_loss': 0})
        
        for pick in self.all_picks:
            if pick.get('status') not in ['win', 'loss', 'push']:
                continue
                
            # Determine prop type from file or data
            prop_type = 'Unknown'
            file_path = pick.get('file_path', '')
            
            if 'points' in file_path or 'Points' in str(pick):
                prop_type = 'Points'
            elif 'rebounds' in file_path or 'Rebounds' in str(pick):
                prop_type = 'Rebounds'
            elif 'assists' in file_path or 'Assists' in str(pick):
                prop_type = 'Assists'
            elif '3pt' in file_path or '3PT' in str(pick):
                prop_type = '3-Pointers'
            elif 'passing' in file_path or 'Passing' in str(pick):
                prop_type = 'Passing Yards'
            elif 'rushing' in file_path or 'Rushing' in str(pick):
                prop_type = 'Rushing Yards'
            elif 'receiving' in file_path or 'Receiving' in str(pick):
                prop_type = 'Receiving Yards'
            elif 'receptions' in file_path or 'Receptions' in str(pick):
                prop_type = 'Receptions'
            elif 'atd' in file_path or 'ATD' in str(pick):
                prop_type = 'ATD'
            elif 'spread' in str(pick).lower() or 'moneyline' in str(pick).lower():
                prop_type = 'Main Bets'
                
            prop_stats[prop_type]['picks'] += 1
            prop_stats[prop_type]['profit_loss'] += pick.get('profit_loss', 0)
            
            if pick.get('status') == 'win':
                prop_stats[prop_type]['wins'] += 1
            elif pick.get('status') == 'loss':
                prop_stats[prop_type]['losses'] += 1
            else:
                prop_stats[prop_type]['pushes'] += 1
        
        # Convert to sorted format
        prop_breakdown = {}
        for prop_type, stats in prop_stats.items():
            if stats['picks'] >= 5:  # Minimum 5 picks
                win_rate = stats['wins'] / (stats['wins'] + stats['losses'] + stats['pushes'])
                prop_breakdown[prop_type] = {
                    'total_picks': stats['picks'],
                    'wins': stats['wins'],
                    'losses': stats['losses'],
                    'pushes': stats['pushes'],
                    'win_rate': win_rate,
                    'profit_loss': stats['profit_loss'] / 100,  # Convert to units
                    'roi': (stats['profit_loss'] / (stats['wins'] + stats['losses'] + stats['pushes']) * 100) if (stats['wins'] + stats['losses'] + stats['pushes']) > 0 else 0
                }
        
        # Sort by total picks (most popular props first)
        prop_breakdown = dict(sorted(prop_breakdown.items(), key=lambda x: x[1]['total_picks'], reverse=True))
        
        return prop_breakdown

    def calculate_players_by_prop_type(self):
        """Calculate player performance broken down by specific prop types"""
        players_by_prop = defaultdict(lambda: defaultdict(list))
        
        # NBA team abbreviation mapping
        nba_team_mapping = {
            'Atlanta Hawks': 'atl', 'Boston Celtics': 'bos', 'Brooklyn Nets': 'bkn',
            'Charlotte Hornets': 'cha', 'Chicago Bulls': 'chi', 'Cleveland Cavaliers': 'cle',
            'Dallas Mavericks': 'dal', 'Denver Nuggets': 'den', 'Detroit Pistons': 'det',
            'Golden State Warriors': 'gsw', 'Houston Rockets': 'hou', 'Indiana Pacers': 'ind',
            'LA Clippers': 'lac', 'Los Angeles Lakers': 'lal', 'Memphis Grizzlies': 'mem',
            'Miami Heat': 'mia', 'Milwaukee Bucks': 'mil', 'Minnesota Timberwolves': 'min',
            'New Orleans Pelicans': 'no', 'New York Knicks': 'ny', 'Oklahoma City Thunder': 'okc',
            'Orlando Magic': 'orl', 'Philadelphia 76ers': 'phi', 'Phoenix Suns': 'phx',
            'Portland Trail Blazers': 'por', 'Sacramento Kings': 'sac', 'San Antonio Spurs': 'sa',
            'Toronto Raptors': 'tor', 'Utah Jazz': 'utah', 'Washington Wizards': 'was'
        }
        
        # Map file paths to prop types
        prop_mapping = {
            'nba/nba_points_props_tracking.json': 'Points Props',
            'nba/nba_rebounds_props_tracking.json': 'Rebounds Props',
            'nba/nba_assists_props_tracking.json': 'Assists Props',
            'nba/nba_3pt_props_tracking.json': '3PT Props'
        }
        
        for file_path, prop_type in prop_mapping.items():
            full_path = self.base_dir / file_path
            if not full_path.exists():
                continue
                
            try:
                with open(full_path, 'r') as f:
                    data = json.load(f)
                    
                    # Handle both list format and dict with "picks" key
                    if isinstance(data, dict) and 'picks' in data:
                        picks = data['picks']
                    elif isinstance(data, list):
                        picks = data
                    else:
                        continue
                    
                    for pick in picks:
                        player = pick.get('player')
                        if player and pick.get('status') in ['win', 'loss', 'push']:
                            players_by_prop[prop_type][player].append(pick)
                            
            except Exception as e:
                print(f"Error processing {file_path} for prop analysis: {e}")
                continue
        
        # Calculate metrics for each player within each prop type
        result = {}
        for prop_type, players in players_by_prop.items():
            prop_players = []
            for player, player_picks in players.items():
                if len(player_picks) >= 5:  # Minimum 5 picks to be included
                    wins = len([p for p in player_picks if p.get('status') == 'win'])
                    losses = len([p for p in player_picks if p.get('status') == 'loss'])
                    pushes = len([p for p in player_picks if p.get('status') == 'push'])
                    total_completed = wins + losses + pushes
                    win_rate = wins / total_completed if total_completed > 0 else 0
                    profit_loss = sum(p.get('profit_loss', 0) for p in player_picks)
                    
                    # Get team information from first pick
                    team_name = ''
                    team_abbrev = ''
                    if player_picks:
                        team_name = player_picks[0].get('home_team') or player_picks[0].get('team') or ''
                        if team_name in nba_team_mapping:
                            team_abbrev = nba_team_mapping[team_name]
                    
                    prop_players.append({
                        'name': player,
                        'total_picks': len(player_picks),
                        'wins': wins,
                        'losses': losses,
                        'pushes': pushes,
                        'win_rate': win_rate,
                        'profit_loss': profit_loss / 100,  # Convert to units
                        'team_abbrev': team_abbrev,
                        'team_name': team_name
                    })
            
            # Sort by win rate and take top 10
            prop_players.sort(key=lambda x: x['win_rate'], reverse=True)
            result[prop_type] = prop_players[:10]
        
        return result
    
    def calculate_edge_analysis(self):
        """Calculate edge distribution analysis"""
        edges = [p.get('edge', 0) for p in self.all_picks if p.get('edge') is not None]
        
        if not edges:
            return {
                'avg_edge': 0,
                'median_edge': 0,
                'edge_ranges': {
                    'negative': 0,
                    '0-5': 0,
                    '5-10': 0,
                    '10-15': 0,
                    '15+': 0
                }
            }
        
        avg_edge = sum(edges) / len(edges)
        sorted_edges = sorted(edges)
        median_edge = sorted_edges[len(sorted_edges) // 2]
        
        edge_ranges = {
            'negative': len([e for e in edges if e < 0]),
            '0-5': len([e for e in edges if 0 <= e < 5]),
            '5-10': len([e for e in edges if 5 <= e < 10]),
            '10-15': len([e for e in edges if 10 <= e < 15]),
            '15+': len([e for e in edges if e >= 15])
        }
        
        return {
            'avg_edge': avg_edge,
            'median_edge': median_edge,
            'edge_ranges': edge_ranges
        }
    
    def calculate_ai_score_analysis(self):
        """Calculate AI score distribution analysis"""
        ai_scores = [p.get('ai_score', 0) for p in self.all_picks if p.get('ai_score') is not None]
        
        if not ai_scores:
            return {
                'avg_ai_score': 0,
                'max_ai_score': 0,
                'score_distribution': {
                    '0-2': 0,
                    '2-4': 0,
                    '4-6': 0,
                    '6-8': 0,
                    '8-10': 0
                }
            }
        
        avg_ai_score = sum(ai_scores) / len(ai_scores)
        max_ai_score = max(ai_scores)
        
        score_distribution = {
            '0-2': len([s for s in ai_scores if 0 <= s < 2]),
            '2-4': len([s for s in ai_scores if 2 <= s < 4]),
            '4-6': len([s for s in ai_scores if 4 <= s < 6]),
            '6-8': len([s for s in ai_scores if 6 <= s < 8]),
            '8-10': len([s for s in ai_scores if 8 <= s <= 10])
        }
        
        return {
            'avg_ai_score': avg_ai_score,
            'max_ai_score': max_ai_score,
            'score_distribution': score_distribution
        }
    
    def empty_metrics(self):
        """Return empty metrics structure"""
        return {
            'total_picks': 0,
            'completed_picks': 0,
            'wins': 0,
            'losses': 0,
            'pushes': 0,
            'win_rate': 0,
            'profit_loss': 0,
            'roi': 0
        }
    
    def generate_analytics(self):
        """Generate complete analytics data"""
        self.load_all_tracking_data()
        
        analytics = {
            'overview': self.calculate_overview_metrics(),
            'by_sport': self.calculate_by_sport(),
            'by_model_type': self.calculate_by_model_type(),
            'time_series': self.calculate_time_series(),
            'top_performers': self.calculate_top_performers(),
            'model_breakdown': self.calculate_model_breakdown(),
            'prop_breakdown': self.calculate_prop_breakdown(),
            'players_by_prop': self.calculate_players_by_prop_type(),
            'edge_analysis': self.calculate_edge_analysis(),
            'ai_score_analysis': self.calculate_ai_score_analysis()
        }
        
        return analytics
    
    def render_dashboard(self):
        """Render the HTML dashboard with analytics data"""
        analytics = self.generate_analytics()
        
        # Setup Jinja2 environment
        template_loader = FileSystemLoader(searchpath=self.base_dir)
        template_env = Environment(loader=template_loader)
        template = template_env.get_template("analytics_dashboard_template.html")
        
        # Render template with analytics data
        html_content = template.render(analytics=analytics)
        
        # Update the timestamp in the rendered HTML
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')
        html_content = html_content.replace(
            'Last Updated: 2026-01-13 18:54:33 ET',
            f'Last Updated: {current_time}'
        )
        
        # Write the rendered HTML
        output_path = self.base_dir / "analytics_dashboard.html"
        with open(output_path, 'w') as f:
            f.write(html_content)
            
        # Debug: save analytics data as JSON too
        analytics_path = self.base_dir / "analytics_data.json"
        with open(analytics_path, 'w') as f:
            json.dump(analytics, f, indent=2)
        print(f"Analytics data saved: {analytics_path}")
            
        print(f"Analytics dashboard generated: {output_path}")
        print(f"Total picks analyzed: {analytics['overview']['total_picks']}")
        print(f"Overall P&L: {analytics['overview']['profit_loss']:.2f} units")
        print(f"Overall ROI: {analytics['overview']['roi']:.1f}%")
        print(f"Overall Win Rate: {analytics['overview']['win_rate']*100:.1f}%")
        
        # Debug: print some analytics data
        print(f"DEBUG - Analytics keys: {list(analytics.keys())}")
        print(f"DEBUG - Overview: {analytics['overview']}")

if __name__ == "__main__":
    analytics = SportsAnalytics()
    analytics.render_dashboard()