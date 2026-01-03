# MODE: UNIT TEST GENERATION [STRICT]

Use this when backfilling tests for code that currently has none.

**Protocol:**
Coverage is good, meaningful assertions are better.

1.  **Isolation**: Mock external dependencies (APIs, Databases). Do not rely on "real" data for unit tests.
2.  **Happy Path**: Write one test case that proves the function works with valid input.
3.  **Edge Cases**: Write test cases for null inputs, empty lists, and invalid types.
4.  **Assertion Clarity**: Use descriptive assertions (e.g., `assert result == expected, f"Expected {expected}, got {result}"`).
