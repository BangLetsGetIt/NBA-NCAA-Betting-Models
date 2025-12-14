# Canva Template Card Generation Guide

## Current Status

You have a Canva template (`CourtSide Template.png`) that you want to use for generating player prop cards.

## The Challenge

The Canva Connect API doesn't allow direct programmatic access to user-created designs. However, we can use a **hybrid approach**:

1. **Use your Canva template as a background image**
2. **Overlay text programmatically with PIL**

## How Close Can PIL Get?

PIL can match your template **very closely** if we:
- Use your exact template as the background
- Position text elements precisely
- Match fonts, colors, and sizes

The main limitation is **knowing the exact positions** of where each text element should go in your template.

## Setup Steps

### Step 1: Map Text Positions

1. Open your template in an image editor (Preview, Photoshop, etc.)
2. Identify where each text element should be positioned
3. Edit `text_position_config.json` with exact coordinates

Or use the comparison tool:
```bash
cd /Users/rico/sports-models/nba
python3 interactive_position_mapper.py
```

This creates a side-by-side comparison showing where text is currently positioned.

### Step 2: Adjust Coordinates

Edit `text_position_config.json`:
- `x`: Horizontal position (0 = left edge, 1080 = right edge)
- `y`: Vertical position (0 = top edge, 1350 = bottom edge)
- `font_size`: Text size in pixels
- `color`: RGB color `[red, green, blue]` (0-255 each)
- `bold`: `true` or `false`

### Step 3: Test and Refine

```bash
python3 test_canva_cards.py
```

Review the generated cards and adjust positions as needed.

## Alternative: Full PIL Recreation

If you prefer, we can recreate the entire design programmatically with PIL. This gives:
- ✅ Full control
- ✅ No template dependency
- ✅ Easy to modify
- ⚠️ Requires recreating the design from scratch

## Recommendation

**Use the hybrid approach** (template + PIL overlays) because:
1. Keeps your exact Canva design
2. Just need to map text positions once
3. Then it's fully automated
4. Easy to adjust if design changes

## Files

- `canva_hybrid_generator.py` - Main generator using template + overlays
- `text_position_config.json` - Text position coordinates
- `interactive_position_mapper.py` - Tool to visualize positions
- `precise_template_overlay.py` - Precise overlay version
