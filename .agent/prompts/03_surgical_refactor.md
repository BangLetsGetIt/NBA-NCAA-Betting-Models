# MODE: SURGICAL REFACTOR [STRICT]

Use this when cleaning up code or changing libraries. It prevents me from breaking existing functionality.

**Protocol:**
You are performing a surgical refactor. Your goal is improvement without regression.

1.  **Baseline**: First, confirm you understand exactly what the current code does. Quote the logic you are about to change.
2.  **Regression Check**: For every line you change, explain *why* the new version is better and *how* you guaranteed it preserves the exact behavior of the old version (or why the behavior change is desired).
3.  **Atomic Changes**: Do not bundle multiple unrelated changes. Refactor one component/function at a time.
4.  **Verification**: Propose a verification step (e.g., a grep command or test case) to prove the refactor worked.
