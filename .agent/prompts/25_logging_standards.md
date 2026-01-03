# MODE: LOGGING STANDARDS [STRICT]

Use this when adding observability or debugging logs to an application.

**Protocol:**
Logs are data. Treat them with respect.

1.  **Levels**: Use appropriate levels. `ERROR` for crashes, `WARN` for recoverable issues, `INFO` for major events, `DEBUG` for data crumbs.
2.  **Structure**: Prefer structured logging (JSON) over string concatenation where possible (makes parsing easier).
3.  **Context**: Include "Who, What, Where". (e.g., `User 123 failed to login from IP X` vs `Login failed`).
4.  **No Noise**: Do not log giant objects/arrays in the production loop. It floods disk space/costs money.
