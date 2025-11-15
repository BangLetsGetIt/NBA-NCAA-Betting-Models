# NBA Player Props +EV Finder

## What This Model Does

This model identifies **plus EV** (positive expected value) betting opportunities by:

1. **Devigging the Market** - Removes bookmaker vig to find "fair" probabilities
2. **Calculating Expected Value** - Compares offered odds to fair value
3. **Filtering Edge Plays** - Shows only bets with positive expected value
4. **Ranking by EV%** - Orders plays from highest to lowest edge

## How It Works

### Step 1: Find the Sharpest Market
- Looks at all bookmakers offering the same prop
- Identifies the market with lowest vig (sharpest odds)
- Uses this as the baseline for fair value

### Step 2: Remove the Vig
Uses multiplicative method to find true probabilities:
```
Fair Over Probability = (Implied Over%) / (Implied Over% + Implied Under%)
Fair Under Probability = (Implied Under%) / (Implied Over% + Implied Under%)
```

### Step 3: Calculate Expected Value
For each bookmaker's odds:
```
EV% = [(Decimal Odds × Fair Probability) - 1] × 100
```

### Step 4: Show Only +EV Plays
- Displays only plays where EV% > 0
- Ranks from highest to lowest EV
- Highlights Hard Rock as "MUST PLAY"

## What You See on Each Card

- **EV Badge** - Your expected profit per dollar (e.g., +5.23% means you expect to profit $0.05 per $1 wagered)
- **Your Odds** - What the bookmaker is offering
- **Fair Odds** - What the odds should be without edge
- **Implied Prob** - Bookmaker's implied probability
- **Fair Prob** - True probability after removing vig
- **Market Vig** - How much juice the sharpest book has

## Color Coding

- **Green Cards** - +EV plays on regular books
- **Gold Cards** - +EV plays on Hard Rock (your must-play book)
- **Green Border on Stat** - Indicates your advantageous number

## Important Notes

1. **EV% is not win probability** - It's your expected long-term profit rate
2. **Sharpest market sets baseline** - Fair odds come from the lowest-vig market
3. **All plays shown are +EV** - No break-even or negative EV plays displayed
4. **Hard Rock prioritized** - Always shown with special styling when edge exists

## Beginner-Friendly Explanation

**What is EV%?**
If you see a play with +5% EV, it means over the long run, you expect to make $5 for every $100 you bet on this play. Not every bet wins, but this bet offers good value.

**How to use this:**
1. Higher EV% = Better value
2. Hard Rock plays get priority (your preferred book)
3. Consider bet sizing - bigger edges can justify larger bets
4. These are long-term edges - variance exists in short term

**Why some props aren't shown:**
If a prop isn't on the dashboard, it means no bookmaker is offering +EV odds on either side. The market is efficient on those props.
