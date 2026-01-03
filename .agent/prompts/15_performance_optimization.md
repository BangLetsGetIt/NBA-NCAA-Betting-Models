# MODE: PERFORMANCE OPTIMIZATION [STRICT]

Use this when the user asks to "make it faster" or "fix lag".

**Protocol:**
Optimization must be measured, not guessed.

1.  **Baseline Benchmark**: Run the code *before* changing anything and record the execution time or memory usage.
2.  **Bottleneck ID**: Identify the exact function or loop causing the slowness (explain *why* it is slow, e.g., "nested loops O(n^2)").
3.  **incremental Change**: Apply one optimization at a time.
4.  **Verification Benchmark**: Run the code *after* the change and prove the percentage improvement.
