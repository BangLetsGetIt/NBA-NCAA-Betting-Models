# MODE: TEST DRIVEN DEVELOPMENT [STRICT]

Use this when you want to ensure your code is robust and won't break in the future.

**Protocol:**
You must prove the code works via tests, not just assertion.

1.  **Test First**: Before writing the fix/feature, write a small script/test case that reproduces the issue or defines the expected success criteria.
2.  **Corner Cases**: Include test inputs for boundary conditions (e.g., negative numbers, empty strings, null values).
3.  **Run & Report**: Execute the test script. Show me the output proving it fails (if a bug) or passes (if a feature).
4.  **Green Light**: Only commit the code if the test passes cleanly.
