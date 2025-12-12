# How to Run Your Dashboard Script Properly

## ✅ The Right Way

**Always run from your project folder:**

```bash
cd "/Users/rico/American Betting League"
python3 abl_recap.py
```

This ensures the script looks for images in the right place!

## 📁 Your Folder Structure Should Be:

```
American Betting League/
├── abl_recap.py          ← Your script
├── images/               ← Your screenshots go here
│   ├── screenshot1.png
│   ├── screenshot2.jpg
│   └── bigwin.jpeg
├── history/              ← Auto-created by script
│   └── 2025-10-31.csv
└── dashboard.html        ← Generated output
```

## 📸 Images Will Show in Upload Order

The script now sorts images by **modification time** (oldest first), which means:
- First image you add = shows first
- Second image you add = shows second
- etc.

If you want to change the order, you can:
1. Touch the files in the order you want: `touch image1.png` then `touch image2.png`
2. Or rename them to control alphabetical order: `1_first.png`, `2_second.png`, etc.

## 🔍 When You Run the Script, You'll See:

```
============================================================
AMERICAN BETTING LEAGUE DASHBOARD
============================================================
Running from: /Users/rico/American Betting League
Images folder: /Users/rico/American Betting League/images
History folder: /Users/rico/American Betting League/history
============================================================
```

**Check that "Images folder" path is correct!**  
It should be inside "American Betting League", NOT `/Users/rico/images`

Then later:

```
📸 Images for 'Top Performers' section:
============================================================
Looking in: /Users/rico/American Betting League/images
✅ Found 3 image(s) (in upload order):
  1. images/screenshot1.png
  2. images/screenshot2.jpg
  3. images/bigwin.jpeg
```

## ❌ Common Mistake

**DON'T run from home directory:**
```bash
cd /Users/rico          # ❌ Wrong!
python3 abl_recap.py    # Will look in /Users/rico/images
```

**DO run from project directory:**
```bash
cd "/Users/rico/American Betting League"  # ✅ Correct!
python3 abl_recap.py                       # Will look in American Betting League/images
```

## 💡 Pro Tip: Create an Alias

Add this to your `~/.zshrc` or `~/.bash_profile`:

```bash
alias abl='cd "/Users/rico/American Betting League" && python3 abl_recap.py'
```

Then you can just type `abl` from anywhere to run your dashboard! 🚀

## 🖼️ Adding New Screenshots

1. Save your screenshot to the `images` folder
2. Make sure it's `.png`, `.jpg`, or `.jpeg` format
3. Run the script
4. Images appear in the order you added them!

## 📝 Image File Formats

**Accepted:**
- `.png` ✅
- `.jpg` ✅
- `.jpeg` ✅

**Not Accepted:**
- `.gif` ❌
- `.webp` ❌
- `.heic` ❌ (iPhone default - convert to PNG/JPG first)
- `.pdf` ❌

## Converting iPhone Photos

If you have `.heic` photos from iPhone:
1. Open the photo
2. Export as PNG or JPG
3. Or use: `sips -s format png input.heic --out output.png`
