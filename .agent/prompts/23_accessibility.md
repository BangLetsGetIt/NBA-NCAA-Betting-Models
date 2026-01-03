# MODE: ACCESSIBILITY (A11Y) [STRICT]

Use this when building UI components to ensure they are usable by everyone.

**Protocol:**
The web is for everyone.

1.  **Semantic HTML**: Use `<button>` for actions, `<a>` for navigation. Do not use `<div onClick>`.
2.  **Alt Text**: Verify every `<img>` has meaningful `alt` text (or `alt=""` if decorative).
3.  **Contrast Ratio**: Check text colors against backgrounds. Must be readable (WCAG AA standard).
4.  **Keyboard Nav**: Ensure all interactive elements can be reached and activated using ONLY the Tab and Enter keys.
