# Updating The Odds API Key - Quick Guide

## Files That Need API Key Update

### NBA Models:
1. **nba/nba_3pt_props_model.py** - Line 22
   ```python
   API_KEY = os.environ.get('ODDS_API_KEY', 'default_key')
   ```

2. **nba/nba_rebounds_props_model.py** - Line 23
   ```python
   API_KEY = os.environ.get('ODDS_API_KEY', 'default_key')
   ```

3. **nba/nba_assists_props_model.py** - Line 23
   ```python
   API_KEY = os.environ.get('ODDS_API_KEY', 'default_key')
   ```

4. **nba/nba_model_IMPROVED.py** - Uses environment variable
   ```python
   ODDS_API_KEY = os.getenv('ODDS_API_KEY')
   ```

### Soccer Model:
5. **soccer/soccer_model_IMPROVED.py** - Line 32
   ```python
   ODDS_API_KEY = os.getenv('ODDS_API_KEY')
   ```

## Update Methods

### Option 1: Environment Variable (Recommended)
Set in your shell or `.env` file:
```bash
export ODDS_API_KEY='your_new_key_here'
```

Or in `.env` file:
```
ODDS_API_KEY=your_new_key_here
```

### Option 2: Direct Code Update
Update the default fallback values in the Python files (not recommended, but works)

## What I'll Do

Once you provide the new key, I will:
1. ✅ Update all model files with the new key
2. ✅ Test the API connection
3. ✅ Verify all models can fetch data
4. ✅ Confirm everything works

## Ready When You Are!

Just share your new API key and I'll update everything immediately.

