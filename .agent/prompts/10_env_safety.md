# MODE: ENVIRONMENT SAFETY [STRICT]

Use this when installing new packages or messing with your environment configuration, to avoid breaking your setup.

**Protocol:**
Handle environment changes with extreme caution.

1.  **Dependency Check**: Check if the requested package conflicts with existing installations (`pip freeze`).
2.  **Versioning**: Always specify a version number (e.g., `pandas==2.0.0`) instead of just installing `latest`.
3.  **Isolation**: If possible, suggest using a virtual environment (`venv`).
4.  **Rollback Plan**: Explicitly state how to undo the changes if they break the build (e.g., `pip uninstall X`).
