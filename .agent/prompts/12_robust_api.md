# MODE: ROBUST API CLIENT [STRICT]

Use this when connecting to 3rd party APIs (OpenAI, Twitter, OddsAPI).

**Protocol:**
Assume the API will fail, timeout, or return garbage.

1.  **Rate Limiting**: Implement logic to handle "429 Too Many Requests" (e.g., `time.sleep` or exponential backoff).
2.  **Error Handling**: Wrap requests in `try/except` blocks, specifying exact error types (e.g., `requests.exceptions.Timeout`), not just generic `Exception`.
3.  **Validation**: Validate the types of the response fields (e.g., "Expected list, got dict") before using them.
4.  **Logging**: Log the full request URL and response status code for debugging.
