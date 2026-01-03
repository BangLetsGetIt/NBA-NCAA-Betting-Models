# MODE: SCHEMA SAFETY [STRICT]

Use this when modifying database schemas, JSON structures, or data models.

**Protocol:**
Prevent data loss and ensure backward compatibility.

1.  **Backup**: Requires a snapshot or backup strategy before applying changes.
2.  **Migration Plan**: Explicitly write out the migration steps (e.g., "Add column X", "Backfill default value Y").
3.  **Backward Compatibility**: Ensure the code can handle both the old and new schema versions during the transition (if applicable).
4.  **Rollback**: Define the exact SQL or code steps to revert the change if it fails.
