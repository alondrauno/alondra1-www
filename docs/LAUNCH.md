# Launch checklist and verification

Status of the landing page against the implementation spec (`ALONDRA1-LANDING-SPEC.md`), what was verified and how, and what still needs a decision before or after launch. Nothing in the open items was invented on the page; each one is hidden, disabled, or labeled until it is confirmed.

## Open items (owner decisions)

| Item | Current page behavior | To publish |
| --- | --- | --- |
| Personal plan price and billing period | "Pricing coming soon"; **Upgrade to Personal** is a disabled button | Set `priceLabel`, `periodLabel`, `ctaUrl` (verified checkout or account page), `enabled: true` in `config/site.json`. |
| Archive scope (what, retention, limits) | Labeled exactly "Archive" | Add detail only after the product owner confirms it. |
| Log in / Register destinations | Point to the backend account page of each environment (`https://api.<env>/account/`, email code sign-in) | Verify on dev once the backend runs there; change in `config/site.json` → `environments`. |
| Download destinations | All six platforms show "Coming soon"; **Get App** and **Get Started Free** scroll to `#download` | Mark a platform `available` with its official installer or store URL. Windows 1.3.0 exists but has no published release URL yet (alondra1-windows `release` workflow drafts one on a `v*` tag). |
| Feedback | Dev: a **Feedback** footer link and the "Before you try it" section link to the public issue form of this repository (`.github/ISSUE_TEMPLATE/dev-feedback.yml`, owner decision 2026-11-26). Prod: no feedback link. | Choose a support channel for prod and set `environments.prod.feedbackUrl`. |
| Tablet support | One "Tablet" card, "Coming soon", no "iPad / Android tablet" wording | Confirm support per OS; split the card's destinations if their statuses differ. |
| macOS | "Coming soon" | No macOS scope is defined yet (alondra1-mac). Consider `notSupported` if it is not planned. |
| Privacy, Terms, Contact | Draft pages at `/privacy/`, `/terms/`, `/contact/` (shown on dev with a Draft notice). **Prod publishes neither these pages nor Google Analytics until `config/legal.json` is complete.** | Replace every `[PLACEHOLDER]` in `config/legal.json` (operator name and address, contact and privacy email, representative, register entry, VAT ID, supervisory authority, governing law, email delivery provider, effective date), then have the texts in `src/legal/` reviewed by a lawyer. The privacy policy already covers Google Analytics with consent, Cloudflare, Hetzner (Germany), sign-in email, Cloud Sync, encrypted pictures and archive, retention (30 days after deletion, backups 35 days) and GDPR rights; update it when a provider or feature changes (payments, push notifications). |
| Analytics consent | Done in code: banner with Accept/Decline, Consent Mode v2 defaults *denied*, GTM loads only after Accept, Cookie settings in the footer; the banner links the privacy policy | Apply the container settings in README → *Settings inside the GTM container*, then check with Tag Assistant. Prod loads GTM only once the privacy policy is published (above). |
| Real mobile screenshot | The phone shows a **concept** of a mobile to-do screen, built in HTML/CSS after the real dark Windows To-do UI (`data-concept="mobile-ui"`, alt text says "Illustration") | Replace with a real mobile screenshot once a mobile app exists. |
| Reference images from the spec | `image.png` and the concept mockup were not provided; the design follows the official logo and the real app screenshots in alondra1-windows | None, unless you want closer alignment with the mockup. |
| Paid plans | Personal, Friends & Family, Enterprise shown, all disabled, no prices | Owner-approved prices and billing (backend BILLING_SPEC.md). |
| Web app | **Open Web App** hidden; Web card "Coming soon" | Set `webApp.enabled` once the Web app is verified on that environment. |
| DNS | — | Created by alondra1-infra's prod edge stack (proxied records to the landing tunnel); no shared-landing host. |

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
- `docker compose config` of `compose.yaml` and the first run on the dev landing server (alondra1-infra).
- HTTPS for `alondra1.com`, the `www` → apex redirect, and certificate issuance: after DNS points at the host.
- Container restart after a VM reboot: `restart: unless-stopped` is set; test once on the host.
- Rollback: documented in the README; test once on the host.
- Lighthouse (mobile): not run. Expected strong scores (static HTML, about 26 KB of CSS and JS before gzip, hero is HTML/CSS rather than an image; Google Tag Manager is the only third-party script and loads `async`). Known gap: images are PNG, not WebP/AVIF, because no converter was available; the largest is the 191 KB Windows screenshot, lazy-loaded below the fold.
- Consent flow in a real browser (local, GTM hosts blocked): first visit shows the banner, no Google request, all four v2 signals denied, no cookies; Accept injects GTM once and grants analytics only; a revisit loads GTM right away; Cookie settings reopens the banner with focus on it; Decline deletes `_ga` cookies and removes GTM; a choice older than 12 months is asked again. 21 of 21 checks passed (2026-11-23). The banner measures 351×92 px on a 390 px phone and is one 60 px row on desktop.
- Google Tag Manager in production: open `https://alondra1.com/` with GTM *Preview* or Tag Assistant and confirm the container loads and GA4 receives the page view, with no CSP errors in the browser console.
- Keyboard and screen reader pass on real devices (menu focus handling, Escape, and outside-click are implemented; html-validate runs in CI).

## Launch order

1. alondra1-infra provisions the dev landing server; a merge here deploys the dev variant; check `https://alondra1.dev/` (noindex, dev links, `/healthz`).
2. Approve the prod infrastructure and the prod release of the same digest in alondra1-infra (`promote.yml`).
3. The prod edge stack creates `alondra1.com` and `www.alondra1.com`; check `https://alondra1.com/`, `/healthz`, and `https://www.alondra1.com/` (→ permanent redirect to the apex).
4. Clean up the old Alondra1 entries in shared-landing (alondra1-infra `docs/operations/shared-landing-migration.md`). Until then a full shared-landing deploy may rebuild a now unused `alondra1-landing` container, which exits because it has no `ALONDRA1_ENVIRONMENT`; no DNS points there, and other sites are not affected (`docker compose stop alondra1-landing` silences it).
