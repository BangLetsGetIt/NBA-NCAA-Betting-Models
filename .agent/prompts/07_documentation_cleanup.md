# MODE: DOCUMENTATION & CLEANUP [STRICT]

Use this when the code works but is a mess, or you need to understand it later.

**Protocol:**
Your goal is readability and future-proofing.

1.  **Docstrings**: Add Python docstrings (or equivalent) to every function explaining Args, Returns, and potential Raises.
2.  **Comments**: Add "Why" comments (not just "What") to complex logic blocks. Explain the reasoning.
3.  **Type Hinting**: Add type hints to function signatures.
4.  **Readability Pass**: Rename variables to be self-documenting (e.g., change `x` to `user_input_list`). DO NOT change the logic, only the names/docs.
