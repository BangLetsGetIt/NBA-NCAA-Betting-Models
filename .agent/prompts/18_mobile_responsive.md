# MODE: MOBILE RESPONSIVE [STRICT]

Use this when debugging UI issues specifically on mobile devices or different screen sizes.

**Protocol:**
Mobile-first mindset.

1.  **Viewport Check**: Verify the `<meta name="viewport">` tag exists and is correct.
2.  **Media Query Audit**: Check usage of `@media (max-width: ...)` breakpoints. Are they standard?
3.  **Touch Targets**: Ensure buttons and links are large enough (min 44px) and have adequate spacing.
4.  **Overflow Check**: Check for horizontal scrollbars caused by fixed-width elements (use `max-width: 100%` instead).
