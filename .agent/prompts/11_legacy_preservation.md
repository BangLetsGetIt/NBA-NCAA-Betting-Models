# MODE: LEGACY PRESERVATION [STRICT]

Use this when dealing with old, messy, or "spaghetti" code that you didn't write but need to modify.

**Protocol:**
Touching this code is risky. Minimize the blast radius.

1.  **Scope Containment**: Identify exactly which functions depend on the code you are changing. Do not touch anything outside this scope.
2.  **Comment Archaeology**: Read existing comments to understand the original intent. Preserve them or update them; do not delete them blindly.
3.  **Minimal Diff**: Make the smallest possible change to achieve the goal. Do not "fix style" or "prettify" unrelated lines.
4.  **Verification**: Verify that the unmodified parts of the file still function/import correctly.
