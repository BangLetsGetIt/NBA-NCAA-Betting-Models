# MODE: PRODUCTION STANDARD [STRICT]

Use this when building new features or pages. It prevents me from stripping standards or cutting corners.

**Protocol:**
You are building for a production environment. "Good enough" is unacceptable.

1.  **Consistency Check**: Before writing new code, analyze the existing codebase (especially similar files) to understand the established patterns, naming conventions, and UI layouts.
2.  **Feature Parity**: Ensure the new feature includes ALL standard elements (e.g., navigation, error handling, loading states) present in the rest of the app.
3.  **No Placeholders**: Do not use "TODO" comments or placeholder data unless explicitly asked. Implement the logic fully.
4.  **Self-Correction**: After generating code, review it yourself for "lazy" shortcuts (e.g., hardcoded values, missing checks) and fix them before showing me.
