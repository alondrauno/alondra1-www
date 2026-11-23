# Content and deployment

## Content rules

- Claims on the page come from the Windows app's [README](https://github.com/nikita4sea/alondra1-windows#readme) and [FEATURES.md](https://github.com/nikita4sea/alondra1-windows/blob/main/docs/FEATURES.md). Do not promise features listed there as *Not yet*.
- Privacy statements must stay true: no analytics, trackers, cookies, or third-party fonts and scripts on this site.
- Screenshots and logo files are copied from alondra1-windows `docs/screenshots` and `docs/images`. When the app's look changes, copy the new files into `site/images/` with the same names.
- Use the brand files as they are; do not redraw, recolor, or stretch the bird (alondra1-windows `docs/GUIDELINES.md` → Naming and branding).
- Colors in `site/styles.css` mirror the tokens in alondra1-windows `docs/UI-DESIGN.md`; keep text contrast at WCAG AA (4.5:1) in both themes.

## Deployment

- Every push to `main` runs `ci` and then publishes `site/` with the `deploy` workflow.
- One-time setup: *Settings → Pages → Build and deployment → Source: GitHub Actions*.
- Custom domain: set it in *Settings → Pages*, add a `site/CNAME` file with the same domain, and create the DNS record your provider documents for GitHub Pages.
- Roll back by reverting the commit on `main`; the workflow publishes the previous content again.
