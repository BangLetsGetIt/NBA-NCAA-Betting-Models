# Sports Models Audit Instructions

> **CRITICAL**: These instructions are for a READ-ONLY audit. Do NOT modify any code until the entire audit is complete and approved.

---

## Part 1: Instructions for Agent 1 (Diagnostic Agent)

### Your Mission
You are auditing a sports betting model codebase. Your job is to:
1. Learn the entire codebase structure first
2. Identify all data integrity issues
3. Identify all logic bugs
4. Identify all inconsistencies between models
5. Provide suggestions ONLY - do not implement anything

### RULES
- **DO NOT MODIFY ANY FILES**
- Take your time - thoroughness over speed
- Ask clarifying questions before proceeding if anything is unclear
- Document everything you find, even if it seems minor

---

### Phase 1: Codebase Discovery (Do This First)

**Step 1.1: Map the project structure**
```
Run: find /Users/rico/sports-models -name "*.py" -o -name "*.sh" -o -name "*.json" | head -100
```
List all models, scripts, and data files. Create a mental map.

**Step 1.2: Identify all tracking files**
```
Run: find /Users/rico/sports-models -name "*tracking*.json"
```
These are the critical data files that store all pick history.

**Step 1.3: Identify all model files by sport**
- NBA models: `nba/*.py`
- NFL models: `nfl/*.py`
- NCAAB models: `ncaa/*.py`
- WNBA models: `wnba/*.py`
- Soccer models: `soccer/*.py`

**Step 1.4: Understand the data flow**
For each sport, answer:
1. What script generates picks? (e.g., `nba_points_props_model.py`)
2. Where are picks stored? (e.g., `nba_points_props_tracking.json`)
3. What script grades picks? (e.g., `grade_pending_picks()` function)
4. What script generates HTML output? (e.g., `generate_html_output()`)
5. What is the automation entry point? (e.g., `auto_grader.py`)

---

### Phase 2: Data Integrity Audit

**Step 2.1: For EACH tracking file, run this diagnostic:**
```python
import json
from collections import defaultdict, Counter

def audit_tracking_file(filepath):
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    picks = data.get('picks', [])
    
    print(f"\n=== AUDIT: {filepath} ===")
    print(f"Total picks: {len(picks)}")
    
    # Status breakdown
    statuses = Counter(p.get('status') for p in picks)
    print(f"Status breakdown: {dict(statuses)}")
    
    # Check for duplicates (same player + same game)
    player_game_counts = defaultdict(list)
    for p in picks:
        key = f"{p.get('player')}_{p.get('game_time', '')[:10]}_{p.get('bet_type')}"
        player_game_counts[key].append(p.get('pick_id'))
    
    duplicates = {k: v for k, v in player_game_counts.items() if len(v) > 1}
    if duplicates:
        print(f"⚠️ DUPLICATE ENTRIES FOUND: {len(duplicates)} groups")
        for k, v in list(duplicates.items())[:5]:
            print(f"  - {k}: {len(v)} entries")
    else:
        print("✓ No duplicate entries")
    
    # Check profit_loss values
    graded = [p for p in picks if p.get('status') in ['win', 'loss']]
    zero_profit = [p for p in graded if p.get('profit_loss', 0) == 0]
    if zero_profit:
        print(f"⚠️ ZERO PROFIT_LOSS on graded picks: {len(zero_profit)}")
    else:
        print("✓ All graded picks have profit_loss calculated")
    
    # Check for missing fields
    required_fields = ['player', 'status', 'game_time', 'prop_line', 'odds']
    for field in required_fields:
        missing = [p for p in picks if not p.get(field)]
        if missing:
            print(f"⚠️ Missing '{field}': {len(missing)} picks")
    
    # Calculate actual record
    wins = len([p for p in picks if p.get('status') == 'win'])
    losses = len([p for p in picks if p.get('status') == 'loss'])
    pending = len([p for p in picks if p.get('status') == 'pending'])
    
    print(f"\nRecord: {wins}-{losses} (Pending: {pending})")
    
    # Calculate units
    total_units = sum(p.get('profit_loss', 0) for p in graded) / 100.0
    print(f"Units: {total_units:+.2f}u")

# Run for all tracking files
tracking_files = [
    'nba/nba_points_props_tracking.json',
    'nba/nba_assists_props_tracking.json',
    'nba/nba_rebounds_props_tracking.json',
    'nba/nba_3pt_props_tracking.json',
    'nfl/nfl_passing_yards_props_tracking.json',
    'nfl/nfl_rushing_yards_props_tracking.json',
    'nfl/nfl_receiving_yards_props_tracking.json',
    'nfl/nfl_receptions_props_tracking.json',
    # Add NCAAB, WNBA, Soccer as discovered
]

for f in tracking_files:
    try:
        audit_tracking_file(f)
    except Exception as e:
        print(f"Error reading {f}: {e}")
```

**Step 2.2: Cross-reference with real games**
For each sport with graded picks:
1. What dates have graded picks?
2. How many games actually occurred on those dates?
3. Do the number of graded picks match reality?

---

### Phase 3: Code Logic Audit

**Step 3.1: Audit pick_id generation**
For EACH model file, find where `pick_id` is created. Check:
- Does it include the prop line? (BAD - causes duplicates)
- Does it include just Player + BetType + GameDate? (GOOD)

Search pattern: `grep -n "pick_id" nba/*.py nfl/*.py`

**Step 3.2: Audit grading logic**
For EACH grading function, verify:
1. Is profit_loss calculated on win/loss?
2. Is the actual value (points, yards, etc.) stored?
3. Is the status updated correctly?
4. Are edge cases handled? (DNP, game postponed, push)

**Step 3.3: Audit HTML generation**
For EACH `generate_html_output` function:
1. Does it correctly calculate season record from tracking data?
2. Does it correctly sum profit_loss for units display?
3. Does it filter active plays correctly (not showing old/graded picks)?

**Step 3.4: Audit auto_grader.py**
This is the central automation script. Check:
1. Does it load fresh data before processing each model?
2. Does it handle errors gracefully?
3. Does it correctly call each model's grading function?
4. Does it push to git correctly?

---

### Phase 4: Consistency Audit

**Step 4.1: Compare model structures**
All prop models should have consistent:
- Function names (track_new_picks, grade_pending_picks, generate_html_output)
- Field names in tracking JSON
- HTML output format
- Profit/loss calculation logic

Flag any inconsistencies.

**Step 4.2: Compare tracking JSON schemas**
All tracking files should have the same field structure. Compare:
```python
def compare_schemas(file1, file2):
    with open(file1) as f1, open(file2) as f2:
        picks1 = json.load(f1).get('picks', [])
        picks2 = json.load(f2).get('picks', [])
    
    if picks1 and picks2:
        keys1 = set(picks1[0].keys())
        keys2 = set(picks2[0].keys())
        
        only_in_1 = keys1 - keys2
        only_in_2 = keys2 - keys1
        
        if only_in_1 or only_in_2:
            print(f"Schema mismatch between {file1} and {file2}")
            print(f"  Only in {file1}: {only_in_1}")
            print(f"  Only in {file2}: {only_in_2}")
```

---

### Phase 5: Compile Findings Report

Create a structured report with:

1. **Critical Issues** (data corruption, wrong calculations)
2. **Logic Bugs** (code that doesn't work as intended)
3. **Inconsistencies** (differences between models that should be the same)
4. **Improvement Suggestions** (enhancements, not bug fixes)

For each issue, include:
- File and line number
- Description of the problem
- Impact (how it affects the user)
- Suggested fix (but don't implement)

---

## Part 2: Instructions for Agent 2 (Review Agent)

### Your Mission
You are reviewing Agent 1's diagnostic report. Your job is to:
1. Verify Agent 1's findings are accurate
2. Check if Agent 1 missed anything
3. Prioritize the fixes
4. Estimate risk/impact of each change

### RULES
- **DO NOT MODIFY ANY FILES**
- Question everything - don't assume Agent 1 is correct
- Provide independent verification

---

### Review Checklist

**Step R1: Verify each finding**
For every issue Agent 1 reported:
1. Go to the exact file and line number
2. Confirm the issue exists
3. Confirm the impact assessment is correct
4. Rate your confidence: ✓ Verified, ? Uncertain, ✗ Incorrect

**Step R2: Check for missed issues**
Look for these common problems Agent 1 might have missed:
- Timezone handling (games crossing midnight)
- Race conditions (multiple model runs simultaneously)
- API rate limiting issues
- Missing error handling
- Hardcoded values that should be configurable

**Step R3: Prioritize fixes**
Categorize each confirmed issue:
- **P0 - Critical**: Data is wrong, must fix immediately
- **P1 - High**: Logic bug, causes incorrect behavior
- **P2 - Medium**: Inconsistency, works but could break later
- **P3 - Low**: Enhancement, nice to have

**Step R4: Risk assessment**
For each suggested fix, assess:
- How many files need to change?
- Could the fix break something else?
- Is there a safer alternative?
- Should this be tested on a copy first?

**Step R5: Create implementation order**
Suggest the order of fixes based on:
1. Highest impact first
2. Lowest risk first
3. Group related changes together
4. Identify dependencies between fixes

---

### Final Deliverable

Agent 2 should produce:
1. **Validated Issues List** - Confirmed findings from Agent 1
2. **Additional Issues** - Problems Agent 1 missed
3. **Prioritized Fix Plan** - Ordered list of changes to make
4. **Risk Matrix** - Impact vs. effort for each fix
5. **Recommendation** - Single-sentence summary of next steps

---

## How to Use These Instructions

1. Start a new conversation with a fresh agent
2. Copy-paste **Part 1** only
3. Let Agent 1 complete ALL phases before seeing Part 2
4. Start another new conversation with a different agent
5. Give that agent Agent 1's report + **Part 2**
6. Let Agent 2 complete the review
7. Only after BOTH agents agree should any code changes be made

---

## Example Prompt to Start Agent 1

```
I need you to audit my sports betting models codebase. 

DO NOT CHANGE ANY CODE. This is a diagnostic-only mission.

My workspace is at: /Users/rico/sports-models

Here are your detailed instructions:
[paste Part 1 here]

Start with Phase 1: Codebase Discovery. Take your time.
```

## Example Prompt to Start Agent 2

```
I had another agent audit my codebase. Here is their report:
[paste Agent 1's report here]

Your job is to verify this report and add anything they missed.

DO NOT CHANGE ANY CODE. This is a review-only mission.

Here are your detailed instructions:
[paste Part 2 here]

Start by verifying each finding. Be skeptical.
```
