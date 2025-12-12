# OddsPapi Setup Guide

## Overview
- **Free Tier**: 200 requests/month
- **Features**: Player props, 300+ bookmakers, 60+ sports
- **URL**: https://oddspapi.io/en

## Getting Started

### 1. Sign Up for Free Account
- Go to: https://oddspapi.io/en
- Sign up for free account (200 requests/month)
- Get your API key from the dashboard

### 2. Set API Key
```bash
export ODDSPAPI_API_KEY='your_api_key_here'
```

Or add to your `.env` file:
```
ODDSPAPI_API_KEY=your_api_key_here
```

### 3. Test the API
Run the test script:
```bash
python3 test_oddspapi.py
```

## API Documentation
- Check: https://oddspapi.io/en/docs (or similar)
- Look in your dashboard for API documentation

## Expected Endpoints

Based on typical sports API patterns:

### NBA/Basketball:
- `/sports/basketball/events` - Get upcoming games
- `/sports/basketball/odds` - Get odds for games
- `/sports/basketball/player-props` - Player props (if available)
- `/sports/basketball/odds/{event_id}` - Specific game odds

### Soccer:
- `/sports/soccer/events` - Get upcoming games
- `/sports/soccer/odds` - Get odds for games

### Authentication:
Likely uses:
- Header: `X-API-Key: {API_KEY}`
- Or query param: `?apiKey={API_KEY}`

## Rate Limits
- **200 requests/month** = ~6-7 requests/day
- **Strategy**:
  - Cache responses aggressively
  - Batch requests when possible
  - Run models once per day or less frequently

## Next Steps
1. Get API key from https://oddspapi.io/en
2. Run test script to verify endpoints
3. Update models once structure is confirmed

