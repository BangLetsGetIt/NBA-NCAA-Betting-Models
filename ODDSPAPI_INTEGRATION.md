# OddsPapi Integration Status

## ✅ Working!
- **Base URL Found**: `https://oddspapi.io/api/v1`
- **Sports Endpoint**: `/sports` - Returns list of 59 sports
- **Status**: API is accessible and responding

## Next Steps

### 1. Get API Key
- Sign up at: https://oddspapi.io/en
- Get your API key from dashboard
- Set: `export ODDSPAPI_API_KEY='your_key'`

### 2. Find Correct Endpoints
Once we have the API key, we need to test:
- Events endpoint (upcoming games)
- Odds endpoint (spreads, totals)
- Player props endpoint (if available)

### 3. Test Endpoint Patterns
Likely patterns to test:
- `/events?sportId={id}`
- `/odds?sportId={id}`
- `/sports/{sportId}/events`
- `/sports/{sportId}/odds`
- `/player-props?sportId={id}`

## Current Findings
- ✅ API is accessible
- ✅ Sports list works (59 sports available)
- ⏳ Need API key to test protected endpoints
- ⏳ Need to find basketball and soccer sport IDs

## Rate Limits
- **200 requests/month** = ~6-7 requests/day
- **Strategy**: Cache aggressively, batch requests, run models once daily

