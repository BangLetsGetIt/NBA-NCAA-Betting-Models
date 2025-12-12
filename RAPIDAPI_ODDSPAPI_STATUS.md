# RapidAPI OddsPapi Integration Status

## ✅ API Key Working
- **API Key**: `fbb0933d50mshc354fe927e6bcffp101ecejsndc89e340ec39`
- **Format**: RapidAPI key (confirmed)
- **Base URL**: `https://oddspapi.p.rapidapi.com/v1`
- **Headers Required**:
  ```
  X-RapidAPI-Key: {your_key}
  X-RapidAPI-Host: oddspapi.p.rapidapi.com
  ```

## ✅ Working Endpoints Found
These endpoints return 429 (rate limited) which means they **exist and work**:
- `/v1/matches?sportId=11` - Basketball matches
- `/v1/sports/11/fixtures` - Basketball fixtures
- `/v1/odds/pre-match?sportId=11` - Pre-match odds (404 now, but was 429)
- `/v1/odds/live?sportId=11` - Live odds (was 429)

## ⚠️ Current Issue
- **Rate Limits**: Getting 429 (Too Many Requests)
- **Free Tier**: Likely has very strict rate limits
- **Solution**: Need to wait longer between requests OR check RapidAPI dashboard for actual limits

## 📋 Next Steps

### Option 1: Check RapidAPI Dashboard
1. Go to: https://rapidapi.com
2. Log in with your account
3. Find "OddsPapi" in your subscribed APIs
4. Check the **Documentation** tab for:
   - Exact endpoint names
   - Required parameters
   - Rate limits
   - Response structure

### Option 2: Wait and Retry
- Wait 5-10 minutes for rate limit to reset
- Then test with longer delays (5+ seconds between requests)

### Option 3: Check API Usage
- Go to RapidAPI dashboard
- Check your usage/quota
- See if you've hit daily/monthly limits

## 🎯 What We Need

1. **Exact Endpoint Names** from RapidAPI documentation
2. **Response Structure** - to see how data is formatted
3. **Player Props Endpoint** - if available
4. **Rate Limit Info** - to plan request strategy

## 📝 Test Scripts Created
- `test_rapidapi_oddspapi.py` - Main test script
- Can be run with: `python3 test_rapidapi_oddspapi.py`

## 💡 Recommendation

**Best approach**: Check the RapidAPI dashboard for OddsPapi documentation. The exact endpoint names and structure will be there, which will save us time guessing.

Once we have the documentation, I can:
1. Update all NBA props models
2. Update soccer model  
3. Adapt to the exact response format
4. Add proper rate limiting/caching

