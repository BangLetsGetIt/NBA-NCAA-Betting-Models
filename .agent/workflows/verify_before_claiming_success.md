---
description: Rules before writing new code or making claims about data
---

# Pre-Flight Checklist

Before writing any new code that touches data:

1. **Read `.agent/knowledge/` files first** - They document schemas, conventions, and gotchas
2. **Check existing HTML outputs** - They show the CORRECT values to verify against
3. **Apply sanity checks** - If 122-60 record shows +1282 units, that's impossible. Stop and investigate.

# When User Says Something Is Wrong

1. **Do NOT defend your work** - Assume the user is right
2. **Compare to existing known-good outputs** (HTML files, not just JSON)
3. **Find the actual bug** before responding

# Output Verification

Always run a comparison like:
```bash
grep -o 'relevant_value' existing_output.html
```
And verify your new output matches.
