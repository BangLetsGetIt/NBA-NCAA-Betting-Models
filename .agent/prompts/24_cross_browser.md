# MODE: CROSS-BROWSER [STRICT]

Use this when using modern CSS/JS features to ensure compatibility.

**Protocol:**
Chrome is not the only browser.

1.  **CanIUse**: Check compatibility for new features (e.g., Grid, Flex gap) on `caniuse.com` or similar knowledge base.
2.  **Prefixing**: Determine if vendor prefixes (`-webkit-`, `-moz-`) are needed (or use a tool like Autoprefixer).
3.  **Fallbacks**: Provide a fallback for unsupported features (e.g., a solid color if gradients aren't supported).
4.  **OS Check**: Explicitly consider how fonts/rendering might differ on Mac vs. Windows vs. Linux.
