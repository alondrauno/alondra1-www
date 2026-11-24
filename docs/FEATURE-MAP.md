# Feature map: alondra1.com landing page

Every capability and atomic feature of the landing page, with the file that implements it and the test that enforces it. Use it to plan a change without reading the source. Product features of the apps are mapped in their own repositories ([Windows](https://github.com/alondrauno/alondra1-windows/blob/main/docs/FEATURE-MAP.md), [Android](https://github.com/alondrauno/alondra1-android/blob/main/docs/FEATURE-MAP.md), [backend and parity table](https://github.com/alondrauno/alondra1-backend/blob/main/docs/FEATURE-MAP.md)).

**Status:** **Done**: implemented and tested. **Waiting**: built, but hidden or disabled until the owner sets a value ([LAUNCH.md](LAUNCH.md)). **Gap**: not built.

Tests are in `tests/` (`python -m unittest discover -s tests -t .`), run by CI and by the Docker build.

## Capability overview

| # | Capability | Main files |
| --- | --- | --- |
| 1 | [Page content](#1-page-content-page) | `src/index.html`, `config/site.json`, `build.py` |
| 2 | [Plans and pricing](#2-plans-and-pricing-plan) | `config/site.json` → `plans` |
| 3 | [Downloads and platforms](#3-downloads-and-platforms-dl) | `config/site.json` → `platforms` |
| 4 | [Navigation and accounts](#4-navigation-and-accounts-nav) | `src/index.html`, `src/main.js`, build variables |
| 5 | [Analytics and consent](#5-analytics-and-consent-gtm) | `src/consent.js`, `nginx/snippets/security-headers.inc` |
| 6 | [Look and accessibility](#6-look-and-accessibility-look) | `src/styles.css`, `public/` |
| 7 | [Build, serving and deployment](#7-build-serving-and-deployment-ops) | `build.py`, `nginx/`, `Dockerfile`, `.github/workflows` |

## 1. Page content (`PAGE`)

| ID | Atomic feature | Status | Notes |
| --- | --- | --- | --- |
| PAGE-SEC-01 | Sections in a fixed order: header, hero, to-do benefits (`#features`), free apps (`#free-apps`), how it works (`#how-it-works`), pricing (`#pricing`), final call to action, platforms (`#download`), footer | Done | Test-enforced. |
| PAGE-HERO-01 | Hero with a phone concept of the mobile to-do screen, labeled as an illustration | Done | Replace with a real screenshot once the mobile app is published. |
| PAGE-SHOW-01 | Device showcase with the real Windows To-do screenshot | Done | |
| PAGE-SEO-01 | Canonical URL, Open Graph tags and image, `robots.txt`, `sitemap.xml` | Done | Per environment (`environments.<env>.siteUrl`). |
| PAGE-ENV-01 | One image with a dev and a prod variant, chosen by `ALONDRA1_ENVIRONMENT`; refuses to start otherwise | Done | Test-enforced; container smoke test in CI. |
| PAGE-ENV-02 | dev: `noindex` meta, `robots.txt` Disallow, no sitemap, `X-Robots-Tag`, no analytics | Done | |
| PAGE-ENV-03 | prod never names a dev host; dev never uses a prod site URL | Done | Build fails otherwise. |
| PAGE-404-01 | Not-found page | Done | `src/404.html`. |

## 2. Plans and pricing (`PLAN`)

| ID | Atomic feature | Status | Notes |
| --- | --- | --- | --- |
| PLAN-CFG-01 | Plans from `config/site.json` (`free`, `personal`) | Done | |
| PLAN-RULE-01 | Free lists To-do, Mail, Calendar, Notes, Contacts; Cloud sync and Archive only in paid plans | Done | Build and tests fail otherwise. |
| PLAN-RULE-02 | A paid price may not contain a number until the plan is enabled | Done | |
| PLAN-CTA-01 | A plan button is a link only when enabled with a valid URL; otherwise disabled with a note | Done | |
| PLAN-PRICE-01 | Personal plan price and checkout link | Waiting | Backend catalog lists $5/month as pending approval. |
| PLAN-FAM-01 | Friends & Family and Enterprise plans on the page, disabled until approved | Done | Same four plans as the backend catalog. |
| PLAN-NOTE-01 | Note under the plans: Mail and Contacts on Windows only; prices pending approval | Done | |

## 3. Downloads and platforms (`DL`)

| ID | Atomic feature | Status | Notes |
| --- | --- | --- | --- |
| DL-PLAT-01 | Platform cards: Windows, macOS, Android, iOS, Tablet, Web | Done | |
| DL-MOD-01 | Each card lists its modules; only Windows may list Mail or Contacts | Done | Build fails otherwise. |
| DL-WEB-01 | **Open Web App** button | Waiting | `webApp.enabled` once the Web app is verified. |
| DL-RULE-01 | **Download** only for `available` platforms with an `https` URL; `comingSoon` is not clickable; unreleased platforms can't carry a URL | Done | Test-enforced. |
| DL-PUB-01 | Published download links | Waiting | All platforms show "Coming soon". |

## 4. Navigation and accounts (`NAV`)

| ID | Atomic feature | Status | Notes |
| --- | --- | --- | --- |
| NAV-MENU-01 | Mobile menu: focus handling, Escape, click outside; header state on scroll | Done | `src/main.js`. |
| NAV-ACC-01 | **Log in**, **Register**, **Create account** to the backend account page of the environment | Done | Verify on dev once the backend runs there. |
| NAV-FOOT-01 | Footer links Privacy, Terms, Contact, each shown only when set; footer year | Waiting | URLs not set yet. |
| NAV-LINK-01 | Only `https://`, `mailto:`, `/path` or `#anchor` links; the build fails otherwise | Done | |

## 5. Analytics and consent (`GTM`)

| ID | Atomic feature | Status | Notes |
| --- | --- | --- | --- |
| GTM-LOAD-01 | Google Tag Manager only in the prod variant (`GTM-T6TDXTK3`), after consent | Done | |
| GTM-CONS-01 | Consent Mode v2 basic: every signal denied before consent; nothing from Google loads | Done | |
| GTM-CONS-02 | Banner with equal Accept and Decline; shown on first visit and after 12 months | Done | Choice in `localStorage`. |
| GTM-CONS-03 | Accept grants `analytics_storage` only, then loads GTM | Done | |
| GTM-CONS-04 | Footer **Cookie settings**; declining later deletes GA cookies and reloads | Done | |
| GTM-CSP-01 | CSP allows only Google's GTM and GA4 hosts | Done | |

## 6. Look and accessibility (`LOOK`)

| ID | Atomic feature | Status | Notes |
| --- | --- | --- | --- |
| LOOK-RESP-01 | No horizontal overflow from 320 px to 1440 px; 200 % zoom reflow | Done | Verified in [LAUNCH.md](LAUNCH.md). |
| LOOK-CONT-01 | Text contrast WCAG AA (≥ 4.5:1) | Done | |
| LOOK-BRAND-01 | Logo sizes, favicons, Apple touch icon | Done | `public/`. |
| LOOK-3P-01 | No third-party scripts, styles or fonts other than GTM | Done | Test-enforced. |

## 7. Build, serving and deployment (`OPS`)

| ID | Atomic feature | Status | Notes |
| --- | --- | --- | --- |
| OPS-BUILD-01 | Standard-library Python build: validates config, renders, fingerprints assets into `/assets/` | Done | |
| OPS-SRV-01 | Unprivileged nginx on port 8080, `/healthz`, security headers, caching | Done | |
| OPS-IMG-01 | Docker image runs the tests before it builds | Done | |
| OPS-CI-01 | CI: tests, build, html-validate, link check, container smoke test, gitleaks | Done | |
| OPS-DEP-01 | Release on push to `main`: image by commit, SBOM, provenance, Trivy, cosign; dispatched to alondra1-infra (dev automatic, prod approved) | Done | `release.yml`; no deployment credentials here. |
| OPS-DEP-02 | Deployed Compose file: read-only, non-root, no capabilities, `127.0.0.1:8080` behind the edge connector | Done | `compose.yaml`. |
| OPS-DEP-03 | No shared-landing deployment | Done | Cleanup there after cutover (alondra1-infra). |

## Recipes

- **Publish a download:** set the platform's `status` to `available` and its `downloadUrl` in `config/site.json`, run the tests, merge.
- **Publish a price:** set `priceLabel`, `periodLabel`, `ctaUrl` and `enabled: true` on the plan (owner-approved; keep it in line with the backend catalog).
- **Add a plan or a platform:** add the object to `config/site.json`; the template renders it; extend the rule tests in `tests/` if it brings a new rule.
- **Add a section:** `src/index.html` (in the spec's order), styles in `src/styles.css`, and the section-order test.
- **Add a third-party host:** only with a privacy review; add it to `nginx/snippets/security-headers.inc` and the "no other third-party requests" test.
