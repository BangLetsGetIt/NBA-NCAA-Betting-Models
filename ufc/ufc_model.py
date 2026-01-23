import pandas as pd
import numpy as np
import json
import os
import joblib
from datetime import datetime

class UFCModel:
    def __init__(self, data_dir="ufc/data"):
        self.data_dir = data_dir
        self.fighters_file = os.path.join(data_dir, "fighters_db.json")
        self.fights_file = os.path.join(data_dir, "historical_fights.json")
        self.model_file = os.path.join(data_dir, "ufc_xgboost.pkl")
        
        self.fighters_df = None
        self.fights_df = None
        self.model = None

    def load_data(self):
        """Loads fighter and fight history data"""
        if os.path.exists(self.fighters_file):
            with open(self.fighters_file, 'r') as f:
                self.fighters_df = pd.DataFrame(json.load(f))
                # Basic cleaning
                self.fighters_df['reach'] = self.fighters_df['reach'].apply(self._clean_reach)
                self.fighters_df['height'] = self.fighters_df['height'].apply(self._clean_height)
        
        if os.path.exists(self.fights_file):
            with open(self.fights_file, 'r') as f:
                self.fights_df = pd.DataFrame(json.load(f))

    def _clean_reach(self, val):
        """Converts '74.0"' to 74.0 float"""
        if not val or val == "--": return np.nan
        return float(val.replace('"', '').strip())

    def _clean_height(self, val):
        """Converts '6' 2"' to inches (74.0)"""
        if not val or val == "--": return np.nan
        parts = val.replace('"', '').split("'")
        if len(parts) == 2:
            return (int(parts[0]) * 12) + int(parts[1])
        return np.nan

    def get_fighter_stats(self, name):
        """Retrieves stats for a specific fighter"""
        if self.fighters_df is None: return None
        
        # Normalize input name
        name_clean = " ".join(name.lower().split())
        
        # Create full name column if not exists
        if 'full_name_norm' not in self.fighters_df.columns:
            self.fighters_df['full_name_norm'] = (
                self.fighters_df['first_name'] + " " + self.fighters_df['last_name']
            ).str.lower().str.strip()
            
            # Also add nickname variation handling if needed
        
        # Exact match attempt
        fighter = self.fighters_df[self.fighters_df['full_name_norm'] == name_clean]
        
        if not fighter.empty:
            return fighter.iloc[0]
            
        # Fallback: Try matching just last name if unique? No, too risky in fights.
        # Fallback: Check if name is in "nickname" or inverted?
        
        return None

    def feature_engineering(self, fighter_a, fighter_b):
        """
        Calculates differential features for a matchup.
        Returns a dict of features suitable for the model.
        """
        stats_a = self.get_fighter_stats(fighter_a)
        stats_b = self.get_fighter_stats(fighter_b)
        
        if stats_a is None or stats_b is None:
            return None
            
        # Parse logic
        def parse_stat(val, default=0.0):
            if not val or val == "--": return default
            return float(val.replace("%", ""))

        def parse_record(val):
            # Parse "W" from record if possible, though 'record' only has wins currently due to scraper
            # Better to rely on other stats if available
            if not val: return 0
            return int(val)

        # Basic diffs
        # Note: We need more data points like SLpM (Strikes Landed per Min) in the scraper to be truly effective.
        # But for now we use physical traits + record size as proxy for experience
        
        reach_a = stats_a['reach'] if not pd.isna(stats_a['reach']) else stats_a['height'] # Fallback to height
        reach_b = stats_b['reach'] if not pd.isna(stats_b['reach']) else stats_b['height']
        
        height_a = stats_a['height'] if not pd.isna(stats_a['height']) else 0
        height_b = stats_b['height'] if not pd.isna(stats_b['height']) else 0
        
        wins_a = parse_record(stats_a['record'])
        wins_b = parse_record(stats_b['record'])
            
        features = {
            "reach_diff": reach_a - reach_b,
            "height_diff": height_a - height_b,
            "wins_diff": wins_a - wins_b,
            # "stance_match": 1 if stats_a['stance'] == stats_b['stance'] else 0
        }
        
        return features

    def train(self):
        """
        Trains XGBoost model on historical data
        """
        if self.fights_df is None or self.fighters_df is None:
            print("No training data available. Run load_data() first.")
            return

        print(f"Training on {len(self.fights_df)} historical fights...")
        
        X = []
        y = []
        
        for _, row in self.fights_df.iterrows():
            f1 = row['fighter_1']
            f2 = row['fighter_2']
            result_f1 = row.get('fighter_1_outcome', 'win') # Default to win if missing (legacy data)
            
            # Skip if we can't determine winner (draws/NCs)
            if result_f1 not in ['win', 'loss']:
                # print(f"Skipping {f1} vs {f2}: Result {result_f1}")
                continue
                
            feats = self.feature_engineering(f1, f2)
            if feats:
                X.append(list(feats.values()))
                y.append(1 if result_f1 == 'win' else 0)
                
                # Data Augmentation
                feats_flip = self.feature_engineering(f2, f1)
                X.append(list(feats_flip.values()))
                y.append(0 if result_f1 == 'win' else 1)
            else:
                # Debug why features missing
                s1 = self.get_fighter_stats(f1)
                s2 = self.get_fighter_stats(f2)
                if s1 is None: print(f"Missing stats for: {f1}")
                if s2 is None: print(f"Missing stats for: {f2}")


        if not X:
            print("No valid matchups found for training.")
            return

        from xgboost import XGBClassifier
        
        self.model = XGBClassifier(
            n_estimators=100, 
            learning_rate=0.1, 
            max_depth=3,
            eval_metric='logloss'
        )
        
        self.model.fit(np.array(X), np.array(y))
        
        # Save model
        joblib.dump(self.model, self.model_file)
        print(f"Model trained and saved to {self.model_file} with {len(X)} samples.")

    def predict(self, fighter_a, fighter_b):
        """
        Predicts win probability for Fighter A vs Fighter B.
        """
        if self.model is None:
            try:
                self.model = joblib.load(self.model_file)
            except:
                print("Model not trained yet.")
                return None
                
        features = self.feature_engineering(fighter_a, fighter_b)
        if not features:
            print(f"Could not calculate features for {fighter_a} vs {fighter_b}")
            return None
        
        # Predict
        prob = self.model.predict_proba([list(features.values())])[0][1] # Probability of class 1 (F1 Win)
            
        return {
            "fighter_a": fighter_a,
            "fighter_b": fighter_b,
            "win_prob": float(prob),
            "fair_odds": self._prob_to_american(prob)
        }

    def _prob_to_american(self, prob):
        if prob > 0.5:
            return int(- (prob / (1 - prob)) * 100)
        else:
            return int(((1 - prob) / prob) * 100)

if __name__ == "__main__":
    import sys
    model = UFCModel()
    model.load_data()
    
    if len(sys.argv) > 1 and sys.argv[1] == "train":
        model.train()
        
    # Test prediction
    print(model.predict("Jon Jones", "Stipe Miocic"))
