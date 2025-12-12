# Free Sports Betting API Alternatives

## Current Setup
- **The Odds API**: Quota exhausted (was using for odds/props)
- **NBA API** (nba_api library): ✅ FREE and working (for player stats)
- **The Odds API**: Also used for soccer

## Free API Options Comparison

### 1. **OddsPapi** ⭐ RECOMMENDED
- **Free Tier**: 200 requests/month
- **Features**: 
  - Pre-game REST API access
  - Unlimited sports and bookmakers
  - Historical data
  - Covers 60+ sports, 300+ bookmakers
  - Player props support
- **URL**: https://oddspapi.io/en
- **Best For**: Good balance of features and free requests

### 2. **SportAPIs** ⭐ BEST FREE TIER
- **Free Tier**: 300 requests/day (9,000/month!)
- **Features**:
  - All sports, bookmakers, betting markets
  - Historical odds
  - Real-time odds
  - 25+ bookmakers
- **URL**: https://sportapis.com
- **Best For**: Highest free request limit

### 3. **Sportsbook API**
- **Free Tier**: 50 requests/day (1,500/month)
- **Features**:
  - Real-time odds
  - Major sports (NFL, NBA, MLB, etc.)
  - All betting markets
- **URL**: https://sportsbookapi.com
- **Best For**: Simple, straightforward API

### 4. **OddsApi** (different from The Odds API)
- **Free Tier**: 500 requests (one-time "Newbie" plan)
- **Features**:
  - Live odds with continuous updates
  - Daily updated data
  - Rate-limited full API access
- **URL**: https://www.oddsapi.co
- **Best For**: Testing/trial period

### 5. **The Rundown API**
- **Free Tier**: 750 requests/month
- **Features**:
  - Scores and odds
  - Various popular sports
- **URL**: https://therundown.io (check their site)
- **Best For**: Moderate usage needs

### 6. **Apify's Odds API** (Scraper-based)
- **Free Tier**: Limited usage for testing
- **Features**:
  - Scrapes from BetMGM, Caesars, DraftKings, FanDuel, Bet365
  - Moneylines, spreads, totals
  - Player props (may vary)
- **URL**: https://apify.com/api/odds-api
- **Best For**: If you need specific bookmakers

## Recommendation for Your Models

### For NBA Props Models:
1. **SportAPIs** (300/day) - Best free tier, should cover your needs
2. **OddsPapi** (200/month) - Good if you can batch requests efficiently

### For Soccer Model:
1. **SportAPIs** - Covers soccer/football
2. **OddsPapi** - Also covers soccer

### For NBA Stats:
- **Keep using nba_api library** - It's completely free and working perfectly!

## Implementation Notes

### What You Need:
- **NBA Player Props**: Assists, Rebounds, 3PT
- **NBA Game Odds**: Spreads, Totals
- **Soccer Odds**: Spreads, Totals
- **Player Stats**: Already covered by nba_api (free)

### API Requirements:
- ✅ Player props support
- ✅ Spreads and totals
- ✅ Multiple bookmakers (FanDuel, DraftKings, etc.)
- ✅ Real-time or near-real-time data

## Next Steps

1. **Sign up for SportAPIs** (best free tier - 300/day)
2. **Test with one model** to verify player props support
3. **Update code** to use new API if it works
4. **Keep nba_api** for stats (it's free and working)

## Cost Comparison

| API | Free Tier | Paid Starting Price |
|-----|-----------|---------------------|
| SportAPIs | 300/day | Check website |
| OddsPapi | 200/month | Check website |
| Sportsbook API | 50/day | $10/month |
| The Odds API | 500/month | $10/month |
| The Rundown | 750/month | $49/month |

## Important Notes

⚠️ **Player Props Availability**: Not all free APIs support player props. You'll need to test:
- SportAPIs - Check documentation
- OddsPapi - Claims to support props
- Sportsbook API - May have limited props

⚠️ **Rate Limits**: Free tiers have strict limits. Consider:
- Caching responses
- Batching requests
- Running models less frequently

⚠️ **Data Quality**: Free tiers may have:
- Delayed updates
- Limited bookmakers
- Fewer markets

