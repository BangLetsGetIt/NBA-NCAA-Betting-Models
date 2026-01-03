# MODE: DATA SAFEGUARD [STRICT]

Use this when working with data processing, grading scripts, or CSV/JSON manipulation. Prevents data loss or corruption.

**Protocol:**
You are handling critical data. Zero data loss is tolerated.

1.  **Backup First**: Before performing any write operation, create a backup of the source file.
2.  **Validation**: Write a validation step that checks the data *before* processing (e.g., "row count matches", "columns exist") and *after* processing.
3.  **Non-Destructive**: Whenever possible, write to a *new* file instead of overwriting the original. If overwriting is necessary, verify the new content is valid before the final write.
4.  **Audit Trail**: Log exactly what was changed (e.g., "Removed 3 rows where status='fail'").
