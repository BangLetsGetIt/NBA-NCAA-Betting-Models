# MODE: MODULARIZATION [STRICT]

Use this when breaking up a large, monolithic file into smaller modules or classes.

**Protocol:**
High cohesion, low coupling.

1.  **Dependency Check**: Analyze imports. If a module imports everything, it's not a module, it's a terrifying spiderweb.
2.  **Single Responsibility**: Ensure each new file/class has ONE clear purpose (e.g., `parsers.py` vs `database.py`).
3.  **Public Interface**: Explicitly define what is "public" (can be imported) and what is "internal" (prefix with `_`).
4.  **Circular Import Check**: Verify that moving code won't cause circular dependency errors (Module A needs B, B needs A).
