# Images Not Showing - Troubleshooting Guide

## Quick Diagnosis

**Run this debug script first:**
```bash
python3 debug_images.py
```

This will tell you exactly what's wrong with your images folder.

## Common Issues & Solutions

### Issue 1: Images Folder in Wrong Location

**Problem:** The `images` folder needs to be in the **same directory** as your `abl_recap.py` script.

**Check:**
```
your-project/
├── abl_recap.py       ← Your script is here
├── images/            ← Images folder must be here (same level)
│   ├── screenshot1.png
│   └── screenshot2.jpg
└── dashboard.html     ← Generated output
```

**Not this:**
```
your-project/
├── abl_recap.py
└── some-other-folder/
    └── images/        ← Wrong! Not in same directory
```

### Issue 2: Wrong File Extensions

**Problem:** Files must end with `.png`, `.jpg`, or `.jpeg` (lowercase extensions work too)

**Valid:**
- `screenshot.png` ✅
- `bigwin.jpg` ✅
- `photo.jpeg` ✅
- `IMAGE.PNG` ✅

**Invalid:**
- `screenshot.gif` ❌
- `screenshot.webp` ❌
- `screenshot.pdf` ❌
- `screenshot` (no extension) ❌

### Issue 3: Hidden Files

**Problem:** macOS creates hidden `.DS_Store` files that might confuse things

**Solution:** The script already ignores these, but make sure your actual image files aren't hidden (don't start with a dot)

### Issue 4: Folder is Empty

**Problem:** The `images` folder exists but has no files in it

**Solution:** Add your screenshot files to the folder

### Issue 5: Dashboard HTML and Images Not in Same Location

**Problem:** When you open `dashboard.html`, it looks for images in a **relative path**. If you moved the HTML file but not the images folder, the images won't load.

**Solution:** Keep this structure when viewing the dashboard:
```
your-project/
├── dashboard.html     ← Open this file
└── images/            ← Browser looks for images here
    └── screenshot.png
```

If you move `dashboard.html` to a different folder, move the `images` folder with it!

## Step-by-Step Fix

1. **Navigate to where your script is:**
   ```bash
   cd /path/to/your/abl_recap.py
   ```

2. **Check if images folder exists:**
   ```bash
   ls -la
   ```
   You should see an `images/` folder in the list

3. **Check what's in the images folder:**
   ```bash
   ls -la images/
   ```
   You should see your `.png`, `.jpg`, or `.jpeg` files

4. **Add your screenshots if folder is empty:**
   - Copy your screenshot files into the `images` folder
   - Make sure they have `.png`, `.jpg`, or `.jpeg` extensions

5. **Run the debug script:**
   ```bash
   python3 debug_images.py
   ```

6. **Run your main script:**
   ```bash
   python3 abl_recap.py
   ```
   
   Look for this section in the output:
   ```
   📸 Images for 'Top Performers' section:
   ============================================================
   ✅ Found 3 image(s):
     - images/screenshot1.png
     - images/screenshot2.jpg
     - images/bigwin.jpeg
   ```

7. **Open dashboard.html** (in the **same folder** as the images folder)

## Still Not Working?

If images still don't show in the browser but the script says it found them:

**Check the browser console:**
1. Open `dashboard.html`
2. Right-click → Inspect → Console tab
3. Look for errors like "Failed to load resource" or "404 Not Found"

**Common browser issues:**
- Dashboard HTML was moved without the images folder
- Images have spaces or special characters in filenames (use underscores instead)
- File permissions issue (try running: `chmod 644 images/*`)

## Test With a Simple Image

Create a test to verify it works:

1. Download any small image and save as `test.png` in the `images` folder
2. Run `python3 abl_recap.py`
3. Check the console output - it should show `✅ Found 1 image(s): images/test.png`
4. Open `dashboard.html` - the image should appear

If this works, the issue is with your other image files!
