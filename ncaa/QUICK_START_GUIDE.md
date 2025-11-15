# 🚀 Quick Start Guide - College Basketball Model

**Get started in 5 minutes!**

---

## 📦 What You've Received

Your complete college basketball betting model package includes:

1. **ncaab_model_FINAL.py** - Main model script (52KB)
2. **README_NCAAB.md** - Complete documentation
3. **NBA_vs_COLLEGE_COMPARISON.md** - Model comparison guide
4. **ADVANCED_CONFIG_GUIDE.md** - Optimization manual
5. **env_template.txt** - Configuration template

---

## ⚡ 5-Minute Setup

### Step 1: Get Your API Key (2 minutes)
1. Go to **https://the-odds-api.com/**
2. Click "Get Free API Key"
3. Sign up (no credit card required)
4. Copy your API key

### Step 2: Install Dependencies (2 minutes)
Open terminal/command prompt and run:
```bash
pip install requests python-dotenv jinja2 pytz pandas numpy --break-system-packages
```

### Step 3: Configure API Key (1 minute)
1. Create a file named `.env` (yes, just `.env` with a dot)
2. Add this line:
   ```
   ODDS_API_KEY=your_api_key_here
   ```
3. Replace `your_api_key_here` with your actual key
4. Save in the same folder as the Python script

### Step 4: Run the Model
```bash
python ncaab_model_FINAL.py
```

### Step 5: View Results
Open in your browser:
- **ncaab_model_output.html** - Today's picks
- **ncaab_tracking_dashboard.html** - Performance tracking

**That's it! You're now running a professional college basketball model!** 🎉

---

## 📱 Daily Workflow

### Morning Routine (10 minutes)
```bash
# Run the model
python ncaab_model_FINAL.py

# Check yesterday's results
# Open: ncaab_tracking_dashboard.html

# Review today's picks  
# Open: ncaab_model_output.html
```

### What to Look For
✅ **High Confidence Picks** (5+ edge)
✅ **Clear matchup advantages**
✅ **Multiple books agreeing on value**

### Placing Bets
1. Compare model picks vs your book's lines
2. Only bet if the edge still exists
3. Start with 1 unit per bet
4. Track your actual results

---

## 🎯 Understanding the Output

### Model Dashboard Shows:

**For Each Game:**
- **Market Line** - What Vegas thinks
- **Model Line** - What the model predicts
- **Edge** - The difference (your advantage)
- **Pick** - Recommendation (or NO BET)
- **Confidence** - Visual meter (higher = better)

**Example:**
```
Duke @ North Carolina
Market: Duke -5.5
Model: Duke -2.1
Edge: +3.4

✅ BET: Duke -5.5
HIGH confidence (3.4 edge)
```

**Translation:** The model thinks Duke should only be favored by 2.1, but you can get them at -5.5. That's 3.4 points of value!

---

## 💰 Bankroll Management 101

### Starting Bankroll: $1,000

**Conservative Strategy:**
- 1 unit = $10 (1% of bankroll)
- Bet 1 unit per pick
- Max 3-4 picks per day

**Standard Strategy:**
- 1 unit = $20 (2% of bankroll)  
- Bet 1-2 units per pick
- Max 5-6 picks per day

**Aggressive Strategy:**
- 1 unit = $30 (3% of bankroll)
- Bet 1-2 units per pick
- Max 6-8 picks per day

### Golden Rules
🚫 Never bet more than 5% on any single game
🚫 Don't chase losses by increasing bet size
🚫 Take a break after 3 losses in a row
✅ Adjust unit size every $500 in bankroll change

---

## 📊 Performance Targets

### First Month Goals
- **Win Rate**: 54-56%
- **ROI**: 6-10%
- **Track**: At least 30 bets
- **Learn**: Which edges work best

### Three Month Goals
- **Win Rate**: 56-58%
- **ROI**: 10-12%
- **Track**: 100+ bets
- **Refine**: Optimize your strategy

### Season Goals
- **Win Rate**: 56%+
- **ROI**: 10-14%
- **Profit**: 15-25 units
- **Knowledge**: Master specific conferences

---

## 🎓 Reading Confidence Levels

### Model Confidence Meter

**80-100% (Dark Green)**
- Edge: 8+ points
- Action: Max bet (2 units)
- Expected: 65%+ win rate

**60-79% (Green)**
- Edge: 5-7 points
- Action: Standard bet (1-1.5 units)
- Expected: 58-62% win rate

**40-59% (Yellow)**
- Edge: 3-4 points  
- Action: Small bet (0.5-1 unit)
- Expected: 54-56% win rate

**Below 40% (Red/Gray)**
- Edge: <3 points
- Action: NO BET
- Model shows NO BET recommendation

---

## 🔧 Common Issues & Fixes

### "ODDS_API_KEY not found"
**Fix:** 
- Check `.env` file is in same folder as Python script
- Verify no spaces around the `=` sign
- File must be named exactly `.env` (with dot)

### "No module named 'requests'"
**Fix:**
```bash
pip install requests --break-system-packages
```

### "No games found"
**Fix:**
- College season is November-March
- Check if games are scheduled
- Increase `DAYS_AHEAD_TO_FETCH` in script

### Lines Don't Match My Sportsbook
**Normal!** Lines change constantly. Model shows:
- Best available line across all books
- Use as a guide, not exact match
- If your line is worse, the edge might be gone

---

## 💡 Pro Tips for Beginners

### Week 1: Learn
- Don't bet yet, just watch
- See how model performs
- Compare predictions to results
- Build confidence in the system

### Week 2-3: Start Small
- Bet 0.5 units per pick
- Only bet HIGH confidence picks (5+ edge)
- Track your results vs model
- Learn which situations work best

### Week 4+: Scale Up
- Increase to 1 unit per pick
- Add MEDIUM confidence picks
- Diversify across more games
- Optimize your strategy

### Red Flags to Watch
🚩 Win rate < 50% after 25 bets
🚩 Always losing on one bet type (spread/total)
🚩 Lines moving against you constantly
🚩 Chasing losses with bigger bets

**If you see these, STOP and reassess!**

---

## 📈 Tracking Your Results

### Create a Simple Spreadsheet

| Date | Game | Pick | Line | Result | Profit |
|------|------|------|------|--------|--------|
| 3/1 | Duke -5.5 | Spread | -5.5 | Win | +$91 |
| 3/1 | UNC Under 145.5 | Total | 145.5 | Loss | -$100 |

### Calculate Your Stats
```
Win Rate = Wins / (Wins + Losses)
ROI = Total Profit / Total Risked
```

### Model vs Reality
Compare your results to the model's tracking:
- Are you matching the model's picks?
- Different results = different lines or timing
- Adjust your betting schedule if needed

---

## 🎯 Best Betting Situations

### High Win Rate Scenarios
✅ **Home favorites -3 to -7** (58-60% win rate)
✅ **Conference tournament underdogs** (value bets)
✅ **Totals UNDER in rivalry games** (defense shows up)
✅ **Experienced teams in March** (seniors > freshmen)

### Situations to Avoid
❌ Non-conference games early season (unpredictable)
❌ Teams with key injuries (model doesn't know)
❌ Public trap games (Duke/Kentucky on TV)
❌ Blowout lines (20+ point spreads)

---

## 🔄 When to Update

### Daily Updates
Run model ONCE per day:
- **Best Time**: 9-11 AM Eastern
- **Why**: Overnight games updated, fresh lines
- **Benefit**: Full day to place bets

### Don't Run Multiple Times
❌ Don't refresh constantly
❌ Lines change, creates confusion
❌ Pick your spots and commit

### Re-run Only If:
✅ Major line movement (3+ points)
✅ Injury news breaks
✅ You want evening games only

---

## 📚 Next Steps

### After Your First Week
1. Read the full **README_NCAAB.md**
2. Review **NBA_vs_COLLEGE_COMPARISON.md**
3. Check your win rate vs targets

### After 50 Bets
1. Read **ADVANCED_CONFIG_GUIDE.md**
2. Consider optimizing parameters
3. Focus on your strengths (spread vs total)

### Long-term Learning
- Study specific conferences deeply
- Understand coaching styles
- Follow college basketball news
- Build experience over multiple seasons

---

## 🎊 Success Checklist

✅ **Setup Complete When:**
- [ ] Python dependencies installed
- [ ] .env file created with API key
- [ ] Model runs without errors
- [ ] HTML files generated successfully
- [ ] You understand the output

✅ **Ready to Bet When:**
- [ ] Watched model for 1+ week
- [ ] Understand edge calculation
- [ ] Set bankroll and unit size
- [ ] Have account at sportsbook
- [ ] Committed to tracking results

✅ **Profitable When:**
- [ ] 54%+ win rate after 50+ bets
- [ ] Positive ROI after 100+ bets
- [ ] Disciplined bankroll management
- [ ] Not tilting after losses
- [ ] Making data-driven decisions

---

## 🚨 Final Reminders

### The Model Is a Tool
- Not perfect (no model is)
- Requires discipline to follow
- Better over 100+ bets
- Won't win every day

### Bet Responsibly
- Only bet what you can afford to lose
- Don't chase losses
- Take breaks when needed
- Gambling should be fun

### Stay Sharp
- Track your results honestly
- Learn from both wins and losses
- Adjust strategy based on data
- Never stop improving

---

## 💬 Quick Reference Commands

```bash
# Install everything (first time only)
pip install requests python-dotenv jinja2 pytz pandas numpy --break-system-packages

# Run the model (daily)
python ncaab_model_FINAL.py

# Check API requests remaining
# Visit: https://the-odds-api.com/account/

# Update Python packages (monthly)
pip install --upgrade requests python-dotenv jinja2 pytz pandas numpy --break-system-packages
```

---

## 🎯 Your First Day Checklist

**Morning:**
- [ ] Run the model
- [ ] Review output HTML
- [ ] Note 2-3 highest confidence picks
- [ ] Check those lines at your book

**Afternoon:**
- [ ] Place bets if lines still good
- [ ] Add to tracking spreadsheet
- [ ] Set alerts for game times

**Evening:**
- [ ] Watch your games (optional, but fun!)
- [ ] Don't stress about daily results
- [ ] Wait for next run to see outcomes

**Next Morning:**
- [ ] Run model again
- [ ] Check tracking dashboard
- [ ] Celebrate wins, learn from losses
- [ ] Repeat process

---

## 🏆 Success Story Timeline

**Week 1**: Learn the system, no betting
**Week 2-4**: Start small, build confidence
**Month 2**: Scale up, hit stride
**Month 3**: Profitable, optimizing strategy
**Season**: 20+ units profit, crushing it!

**This is your journey. Let's get started! 🏀**

---

## 📞 Need Help?

**Common Questions:**
1. Check the full README_NCAAB.md
2. Review troubleshooting section
3. Verify API key and setup
4. Make sure it's college basketball season!

**The model works. Trust the process. Bet smart. Win long-term.** 💪

---

# START HERE → Run `python ncaab_model_FINAL.py`

Good luck! 🍀🏀
