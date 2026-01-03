# MODE: ROOT CAUSE ANALYSIS [STRICT]

Use this when fixing bugs, layout issues, or when something "just isn't working." It prevents me from making lazy edits.

**Protocol:**
Do NOT write any code or fixes yet. You are in DIAGNOSTIC MODE only.

1.  **Audit**: Read the relevant files. Quote the exact lines of code that you suspect are causing the issue.
2.  **Verify**: Check for structural integrity (e.g., closing tags, bracket nesting, variable scope). Do not assume the structure is correct just because it looks okay at a glance.
3.  **Hypothesize & Prove**: State your hypothesis for the failure and explain *why* it fails based *only* on the code you see.
4.  **Stop**: Wait for my confirmation that your diagnosis is correct before implementing any fix.

**Constraint**: If you cannot point to the specific line of code causing the failure, you are not allowed to propose a fix.
