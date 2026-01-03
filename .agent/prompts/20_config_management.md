# MODE: CONFIG MANAGEMENT [STRICT]

Use this when modifying `.env`, `settings.py`, or handling secrets.

**Protocol:**
Prevent leaks and ensuring portability.

1.  **No Hardcoding**: Reject any code that puts secrets directly in Python files.
2.  **Default Values**: Using `os.getenv('KEY', 'default')` is safer than `os.environ['KEY']` (prevents crash on missing key).
3.  **Type Conversion**: Explicitly convert env vars (which are strings) to the needed type (int/bool).
4.  **Example File**: If adding a new env var, update `.env.example` so other developers know about it.
