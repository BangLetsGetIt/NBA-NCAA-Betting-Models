# SportAPIs Setup Guide

## Getting Started

### 1. Sign Up for Free Account
- Go to: https://sportapis.com
- Sign up for free account (300 requests/day)
- Get your API key from the dashboard

### 2. Set API Key
```bash
export SPORTAPIS_API_KEY='your_api_key_here'
```

Or add to your `.env` file:
```
SPORTAPIS_API_KEY=your_api_key_here
```

### 3. Test the API
Run the test script:
```bash
python3 test_sportapis.py
```

## API Documentation

**Note**: SportAPIs documentation may be at:
- https://sportapis.com/docs
- https://docs.sportapis.com
- Check your dashboard for API documentation link

## Common Endpoints (Need to Verify)

Based on typical sports API patterns, SportAPIs likely uses:

### NBA Endpoints:
- `/sports/basketball_nba/events` - Get upcoming games
- `/sports/basketball_nba/odds` - Get odds for games
- `/sports/basketball_nba/odds/{event_id}` - Get odds for specific game
- `/sports/basketball_nba/player-props` - Player props (if available)

### Soccer Endpoints:
- `/sports/soccer/events` - Get upcoming games
- `/sports/soccer/odds` - Get odds for games
- `/sports/soccer/odds/{event_id}` - Get odds for specific game

### Authentication:
Most likely uses one of:
- Header: `Authorization: Bearer {API_KEY}`
- Header: `X-API-Key: {API_KEY}`
- Query param: `?apiKey={API_KEY}`

## Next Steps

1. **Get API Key** from https://sportapis.com
2. **Check Documentation** for exact endpoints and authentication
3. **Test with test_sportapis.py** to verify structure
4. **Update models** once we confirm the API structure

## Important Notes

⚠️ **Player Props**: Not all APIs support player props in free tier. You'll need to:
- Check SportAPIs documentation
- Test the player props endpoint
- Verify it includes assists, rebounds, 3PT props

⚠️ **Rate Limits**: 300 requests/day = ~12 requests/hour
- Cache responses when possible
- Batch requests efficiently
- Consider running models less frequently

⚠️ **Data Structure**: Each API has different response formats
- We'll need to adapt the code to match SportAPIs format
- May need to map team names, player names, etc.

