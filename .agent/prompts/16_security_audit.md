# MODE: SECURITY AUDIT [STRICT]

Use this when hardening an application or checking for vulnerabilities.

**Protocol:**
Paranoid mode enabled. Trust no input.

1.  **Input Validation**: Check that ALL user inputs (API params, form data) are validated and sanitized.
2.  **Secret Management**: Scan for hardcoded API keys, passwords, or tokens. Recommend moving them to `.env`.
3.  **Dependency Scan**: Check for outdated or vulnerable libraries.
4.  **Least Privilege**: Ensure file permissions and API scopes are as restrictive as possible.
