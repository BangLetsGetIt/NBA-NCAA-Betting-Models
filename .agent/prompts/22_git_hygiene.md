# MODE: GIT HYGIENE [STRICT]

Use this when creating commits, branches, or merging code.

**Protocol:**
Your git history is your professional legacy. Keep it clean.

1.  **Atomic Commits**: One logical change per commit. Do not mix "Fix bug A" with "Refactor Feature B".
2.  **Message Format**: Use the format `type: subject` (e.g., `fix: resolve crash on startup`, `feat: add user login`).
3.  **No Junk**: Verify no `.DS_Store`, `__pycache__`, or temp files are being added (check `.gitignore` first).
4.  **Self-Review**: Run `git diff --staged` before committing to catch accidental debug prints left in the code.
