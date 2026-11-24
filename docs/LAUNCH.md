# Launch checklist and verification

Status of the landing page against the implementation spec (`ALONDRA1-LANDING-SPEC.md`), what was verified and how, and what still needs a decision before or after launch. Nothing in the open items was invented on the page; each one is hidden, disabled, or labeled until it is confirmed.

## Open items (owner decisions)

| Item | Current page behavior | To publish |
| --- | --- | --- |
| Personal plan price and billing period | "Pricing coming soon"; **Upgrade to Personal** is a disabled button | Set `priceLabel`, `periodLabel`, `ctaUrl` (verified checkout or account page), `enabled: true` in `config/site.json`. |
| Archive scope (what, retention, limits) | Labeled exactly "Archive" | Add detail only after the product owner confirms it. |
| Log in / Register destinations | Hidden, together with **Create account** | Set `ALONDRA1_LOGIN_URL` and `ALONDRA1_REGISTER_URL` in shared-landing `envs/alondra1-www.env`, rebuild. The backend's email one-time-code API exists, but no web sign-in page does yet. |
| Download destinations | All five platforms show "Coming soon"; **Get App** and **Get Started Free** scroll to `#download` | Mark a platform `available` with its official installer or store URL. Windows 1.3.0 exists but has no published release URL yet (alondra1-windows `release` workflow drafts one on a `v*` tag). |
| Tablet support | One "Tablet" card, "Coming soon", no "iPad / Android tablet" wording | Confirm support per OS; split the card's destinations if their statuses differ. |
| macOS | "Coming soon" | No macOS scope is defined yet (alondra1-mac). Consider `notSupported` if it is not planned. |
| Privacy, Terms, Contact | Not shown | Set the URLs; footer links appear automatically. A privacy policy that names Google Analytics / Tag Manager is needed now that analytics is on. |
| Analytics consent | Done in code: banner with Accept/Decline, Consent Mode v2 defaults *denied*, GTM loads only after Accept, Cookie settings in the footer | Apply the container settings in README → *Settings inside the GTM container*, then check with Tag Assistant. Write the privacy policy (above) and set `PRIVACY_URL`; the banner then links to it. |
| Real mobile screenshot | The phone shows a **concept** of a mobile to-do screen, built in HTML/CSS after the real dark Windows To-do UI (`data-concept="mobile-ui"`, alt text says "Illustration") | Replace with a real mobile screenshot once a mobile app exists. |
| Reference images from the spec | `image.png` and the concept mockup were not provided; the design follows the official logo and the real app screenshots in alondra1-windows | None, unless you want closer alignment with the mockup. |
| DNS | — | A/AAAA for `alondra1.com` and `www.alondra1.com` → the shared-landing host. |

## Verified locally (2026-11-23)

| Check | Result |
| --- | --- |
| Unit and page tests (`python -m unittest discover -s tests -t .`) | 33 passed |
| Horizontal overflow at 320, 360, 375, 390, 768, 1024, 1440 px | None (measured in real viewports with a scrollbar, which is stricter than phones) |
| 200% zoom (1280 px window → 640 CSS px) and 320 CSS px reflow | No overflow, no clipped controls |
| Hero shows the phone mobile UI at every width; desktop keeps the two-column desktop layout | Yes (screenshots in `screenshots/`) |
| Section order | Header, hero, to-do benefits, free apps, how it works, pricing, final CTA, platforms, footer (test-enforced) |
| Text contrast (WCAG AA) | Every text/background pair ≥ 4.5:1; lowest is muted text on lavender at 4.96:1 |
| Anchors, images | Every `#anchor` resolves; every image has alt text and width/height; below-the-fold images lazy-load |
| Third parties | Only the Google Tag Manager container, and only when `GTM_ID` is set (test-enforced); no other external scripts, styles, or fonts |

## Not verified yet (needs Docker, the server, or DNS)

- `docker build` and the container smoke test: run by the `ci` workflow (Docker is not installed on the development machine).
- `docker compose config` with the new `alondra1-landing` service in shared-landing; first run is on the server or in CI.
- HTTPS for `alondra1.com`, the `www` → apex redirect, and certificate issuance: after DNS points at the host.
- Container restart after a VM reboot: `restart: unless-stopped` is set; test once on the host.
- Rollback: documented in the README; test once on the host.
- Lighthouse (mobile): not run. Expected strong scores (static HTML, about 26 KB of CSS and JS before gzip, hero is HTML/CSS rather than an image; Google Tag Manager is the only third-party script and loads `async`). Known gap: images are PNG, not WebP/AVIF, because no converter was available; the largest is the 191 KB Windows screenshot, lazy-loaded below the fold.
- Consent flow in a real browser (local, GTM hosts blocked): first visit shows the banner, no Google request, all four v2 signals denied, no cookies; Accept injects GTM once and grants analytics only; a revisit loads GTM right away; Cookie settings reopens the banner with focus on it; Decline deletes `_ga` cookies and removes GTM; a choice older than 12 months is asked again. 21 of 21 checks passed (2026-11-23). The banner measures 351×92 px on a 390 px phone and is one 60 px row on desktop.
- Google Tag Manager in production: open `https://alondra1.com/` with GTM *Preview* or Tag Assistant and confirm the container loads and GA4 receives the page view, with no CSP errors in the browser console.
- Keyboard and screen reader pass on real devices (menu focus handling, Escape, and outside-click are implemented; html-validate runs in CI).

## Launch order

1. Push `alondra1-www` to `main` and make it cloneable by the server (`DEPLOY_GIT_TOKEN` or a public repository). Add the `DEPLOY_*` secrets to this repository.
2. Merge the shared-landing change. Full deploys clone every site repository, so step 1 must come first or every site's deploy fails.
3. Create the DNS records. Traefik requests the certificates on the first HTTPS request.
4. Check `https://alondra1.com/`, `https://alondra1.com/healthz`, and `https://www.alondra1.com/` (→ permanent redirect to the apex).
