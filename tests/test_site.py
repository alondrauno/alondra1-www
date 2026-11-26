"""Tests for the Alondra1 landing page: content rules from the spec and checks on the built HTML.

    python -I -m unittest discover -s tests -t .
"""

import copy
import json
import re
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

import build

CONFIG = json.loads(build.CONFIG.read_text(encoding="utf-8"))
CONFIG.pop("$comment", None)


def config(**changes):
    data = copy.deepcopy(CONFIG)
    for key, value in changes.items():
        data[key] = value
    return data


class Page(HTMLParser):
    """Collects ids, links, images, scripts, and the order of top-level landmarks and sections."""

    def __init__(self):
        super().__init__()
        self.ids, self.links, self.images, self.scripts, self.styles = set(), [], [], [], []
        self.order, self.buttons, self.meta = [], [], {}
        self.title, self._in_title = "", False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "a":
            self.links.append(a)
        if tag == "img":
            self.images.append(a)
        if tag == "script":
            self.scripts.append(a)
        if tag == "link" and a.get("rel") == "stylesheet":
            self.styles.append(a)
        if tag == "button":
            self.buttons.append(a)
        if tag == "meta" and ("name" in a or "property" in a):
            self.meta[a.get("name") or a.get("property")] = a.get("content", "")
        if tag == "link" and a.get("rel") == "canonical":
            self.meta["canonical"] = a.get("href")
        if tag in ("header", "footer") and "class" in a and a["class"].startswith("site-"):
            self.order.append(a["class"])
        if tag == "section":
            self.order.append(a.get("id") or a.get("class"))
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


# Operator details as they will look once the owner has filled in config/legal.json (test values only).
COMPLETE_LEGAL = {
    "operatorName": "Example Operator", "operatorAddress": "Example Street 1, 10115 Berlin, Germany",
    "contactEmail": "hello@example.com", "privacyEmail": "privacy@example.com", "representative": "Alex Example",
    "registerEntry": "not registered", "vatId": "none", "supervisoryAuthority": "the Berlin Commissioner for Data Protection",
    "governingLaw": "Germany", "emailProvider": "Example Mail GmbH", "effectiveDate": "1 December 2026",
}


def legal_file(data):
    path = Path(tempfile.mkdtemp(prefix="alondra1-legal-")) / "legal.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def built(env=None, environment=None, legal=None):
    out = Path(tempfile.mkdtemp(prefix="alondra1-www-")) / "dist"
    cfg = build.build(out, env=env or {}, year=2026, environment=environment,
                      **({"legal_path": legal_file(legal)} if legal is not None else {}))
    html = (out / "index.html").read_text(encoding="utf-8")
    page = Page()
    page.feed(html)
    return out, cfg, html, page


class LegalPages(unittest.TestCase):
    """Privacy, Terms and Contact: drafts on dev; on prod only when complete, and analytics only with a privacy policy."""

    def page(self, out, slug):
        return (out / slug / "index.html").read_text(encoding="utf-8")

    def test_committed_legal_file_is_valid(self):
        legal = build.load_legal()
        self.assertEqual(set(legal), set(build.LEGAL_FIELDS))

    def test_dev_shows_drafts_with_notice_and_footer_links(self):
        out, cfg, html, page = built(environment="dev", legal={k: f"[{k.upper()}]" for k in build.LEGAL_FIELDS})
        hrefs = [a.get("href") for a in page.links]
        for slug in ("privacy", "terms", "contact"):
            self.assertIn(f"/{slug}/", hrefs)
            text = self.page(out, slug)
            self.assertIn('class="legal-draft"', text)
            self.assertIn('content="noindex, nofollow"', text)

    def test_prod_with_placeholders_publishes_no_pages_and_no_analytics(self):
        legal = dict(COMPLETE_LEGAL, operatorName="[OPERATOR LEGAL NAME]")
        out, cfg, html, page = built(environment="prod", legal=legal)
        for slug in ("privacy", "terms", "contact"):
            self.assertFalse((out / slug).exists())
        self.assertNotIn("data-gtm-id", html)
        self.assertNotIn("/privacy/", (out / "sitemap.xml").read_text(encoding="utf-8"))

    def test_prod_complete_publishes_pages_links_sitemap_and_consent_link(self):
        out, cfg, html, page = built(environment="prod", legal=COMPLETE_LEGAL)
        hrefs = [a.get("href") for a in page.links]
        sitemap = (out / "sitemap.xml").read_text(encoding="utf-8")
        for slug in ("privacy", "terms", "contact"):
            self.assertIn(f"/{slug}/", hrefs)
            self.assertIn(f"<loc>https://alondra1.com/{slug}/</loc>", sitemap)
            text = self.page(out, slug)
            self.assertNotIn("legal-draft", text)
            self.assertIsNone(build.PLACEHOLDER.search(text), f"{slug} still has a placeholder")
            self.assertIn(f'<link rel="canonical" href="https://alondra1.com/{slug}/">', text)
        banner = html[html.index('id="consent"'):]
        self.assertIn('href="/privacy/"', banner)

    def test_privacy_policy_names_what_the_product_does(self):
        out, *_ = built(environment="prod", legal=COMPLETE_LEGAL)
        text = self.page(out, "privacy")
        for fact in ("Google Analytics", "only with your consent", "_ga", "alondra1-consent", "Cookie settings",
                     "Hetzner Online GmbH", "Cloudflare", "Example Mail GmbH", "35 days", "30 days",
                     "not end-to-end encrypted", "privacy@example.com", "Berlin Commissioner"):
            self.assertIn(fact, text)
        contact = self.page(out, "contact")
        for fact in ("Example Operator", "Example Street 1", "hello@example.com", "Alex Example"):
            self.assertIn(fact, contact)

    def test_values_are_escaped_and_emails_checked(self):
        out, *_ = built(environment="dev", legal=dict(COMPLETE_LEGAL, operatorName="A <b>&</b> Co"))
        self.assertIn("A &lt;b&gt;&amp;&lt;/b&gt; Co", self.page(out, "contact"))
        with self.assertRaises(build.ConfigError):
            built(environment="dev", legal=dict(COMPLETE_LEGAL, contactEmail="not an email"))
        with self.assertRaises(build.ConfigError):
            built(environment="dev", legal=dict(COMPLETE_LEGAL, unexpected="x"))


class PlanRules(unittest.TestCase):
    def test_free_plan_has_all_five_core_apps(self):
        free = next(p for p in CONFIG["plans"] if p["id"] == "free")
        for app in ("To-do", "Mail", "Calendar", "Notes", "Contacts"):
            self.assertIn(app, free["features"])

    def test_cloud_sync_and_archive_only_in_paid_plans(self):
        for plan in CONFIG["plans"]:
            for feature in ("Cloud sync", "Archive"):
                if plan["id"] == "free":
                    self.assertNotIn(feature, plan["features"])
                else:
                    self.assertIn(feature, plan["features"])

    def test_paid_plan_does_not_gate_core_apps(self):
        for plan in CONFIG["plans"]:
            if plan["id"] != "free":
                self.assertFalse({"To-do", "Mail", "Calendar", "Notes", "Contacts"} & set(plan["features"]))

    def test_plan_fields(self):
        fields = {"id", "name", "priceLabel", "periodLabel", "description", "features", "ctaLabel", "ctaUrl",
                  "featured", "enabled"}
        for plan in CONFIG["plans"]:
            self.assertEqual(fields, set(plan))

    def test_validation_rejects_cloud_sync_in_free(self):
        bad = config()
        bad["plans"][0]["features"].append("Cloud sync")
        with self.assertRaises(build.ConfigError):
            build.validate(bad)

    def test_validation_rejects_missing_core_app(self):
        bad = config()
        bad["plans"][0]["features"].remove("Notes")
        with self.assertRaises(build.ConfigError):
            build.validate(bad)

    def test_validation_rejects_enabled_plan_without_url(self):
        bad = config()
        bad["plans"][1]["enabled"] = True
        bad["plans"][1]["ctaUrl"] = ""
        with self.assertRaises(build.ConfigError):
            build.validate(bad)

    def test_no_unconfirmed_prices(self):
        for plan in CONFIG["plans"]:
            if plan["id"] != "free" and not plan["enabled"]:
                self.assertNotRegex(plan["priceLabel"], r"\d", "show a price only once the owner approves it")


class PlatformRules(unittest.TestCase):
    def test_all_five_platforms_in_order(self):
        self.assertEqual([p["id"] for p in CONFIG["platforms"]], ["windows", "macos", "android", "ios", "tablet", "web"])

    def test_available_requires_https_download(self):
        bad = config()
        bad["platforms"][0]["status"] = "available"
        with self.assertRaises(build.ConfigError):
            build.validate(bad)
        bad["platforms"][0]["downloadUrl"] = "http://example.com/setup.exe"
        with self.assertRaises(build.ConfigError):
            build.validate(bad)

    def test_unreleased_platform_cannot_have_download(self):
        bad = config()
        bad["platforms"][2]["downloadUrl"] = "https://example.com/app.apk"
        with self.assertRaises(build.ConfigError):
            build.validate(bad)

    def test_download_button_only_for_available(self):
        good = config()
        good["platforms"][0].update(status="available", downloadUrl="https://example.com/Alondra1-setup.exe")
        html = build.platforms_html(good)
        self.assertEqual(html.count(">Download</a>"), 1)
        self.assertIn('href="https://example.com/Alondra1-setup.exe"', html)
        self.assertEqual(html.count("Coming soon"), 5)


class LinkRules(unittest.TestCase):
    def test_env_overrides_links(self):
        cfg = build.load_config(env={"LOGIN_URL": "https://app.example.com/login",
                                     "REGISTER_URL": "https://app.example.com/register"})
        self.assertEqual(cfg["links"]["login"], "https://app.example.com/login")

    def test_plain_http_refused(self):
        with self.assertRaises(build.ConfigError):
            build.load_config(env={"LOGIN_URL": "http://app.example.com/login"})

    def test_site_url_must_be_https_origin(self):
        with self.assertRaises(build.ConfigError):
            build.load_config(env={"SITE_URL": "https://alondra1.com/"})


class BuiltPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out, cls.cfg, cls.html, cls.page = built()

    def test_title_canonical_and_description(self):
        self.assertEqual(self.page.title, "Alondra1 — Personal To-Do & Daily Planning App")
        self.assertEqual(self.page.meta["canonical"], "https://alondra1.com/")
        self.assertIn("personal", self.page.meta["description"].lower())
        self.assertTrue(self.page.meta["og:image"].startswith("https://alondra1.com/"))

    def test_not_noindex(self):
        self.assertNotIn("noindex", self.html)
        self.assertIn("Allow: /", (self.out / "robots.txt").read_text())
        self.assertIn("<loc>https://alondra1.com/</loc>", (self.out / "sitemap.xml").read_text())

    def test_section_order(self):
        expected = ["site-header", "hero", "features", "free-apps", "how-it-works", "pricing",
                    "section final-cta", "download", "site-footer"]
        self.assertEqual(self.page.order, expected)

    def test_hero_features_mobile_app(self):
        hero = self.html[self.html.index('class="hero"'):self.html.index('id="features"')]
        self.assertIn('data-concept="mobile-ui"', hero)
        self.assertIn("My Day", hero)
        self.assertNotIn("windows-todo", hero, "the hero must show the mobile app, not a desktop screenshot")

    def test_spec_copy(self):
        for text in ("Your personal to-do companion", "Organize your day.", "Simplify your life.",
                     "More than to-dos. All the essentials, free.", "A calmer way to manage your everyday tasks.",
                     "Your tasks, wherever life takes you.",
                     "Choose the version of Alondra1 that works for your device.", "Capture tasks quickly",
                     "Plan your day", "Keep personal lists", "Stay on track"):
            self.assertIn(text, self.html)

    def test_internal_anchors_resolve(self):
        for link in self.page.links:
            href = link.get("href", "")
            self.assertTrue(href, f"empty href: {link}")
            self.assertNotEqual(href, "#", "dead link")
            if href.startswith("#"):
                self.assertIn(href[1:], self.page.ids, f"missing anchor target {href}")

    def test_header_destinations(self):
        hrefs = [l["href"] for l in self.page.links]
        for anchor in ("#features", "#pricing", "#download"):
            self.assertIn(anchor, hrefs)
        self.assertGreaterEqual(hrefs.count("#download"), 3, "Get App in header, hero, and final CTA")

    def test_unconfigured_auth_is_hidden(self):
        self.assertNotIn(">Log in<", self.html)
        self.assertNotIn(">Register<", self.html)
        self.assertNotIn("Create account", self.html)

    def test_configured_auth_is_shown(self):
        _, _, html, _ = built({"LOGIN_URL": "https://app.example.com/login",
                               "REGISTER_URL": "https://app.example.com/register"})
        self.assertIn('href="https://app.example.com/login"', html)
        self.assertIn('href="https://app.example.com/register"', html)
        self.assertIn(">Create account<", html)

    def test_pricing_before_platforms_and_no_fake_prices(self):
        self.assertLess(self.html.index('id="pricing"'), self.html.index('id="download"'))
        self.assertNotRegex(self.html, r"[$€£]\s?\d")
        self.assertNotIn("Lifetime", self.html)
        self.assertIn("Pricing coming soon", self.html)

    def test_disabled_paid_cta_is_a_disabled_button(self):
        self.assertTrue(any("disabled" in b for b in self.page.buttons))

    def test_platforms_are_last_section_and_have_no_fake_downloads(self):
        self.assertEqual(self.page.order[-2:], ["download", "site-footer"])
        self.assertNotIn(">Download</a>", self.html)
        self.assertEqual(self.html.count('data-status="comingSoon"'), 6)

    def test_images_have_alt_and_dimensions(self):
        for img in self.page.images:
            self.assertIn("alt", img, img)
            self.assertIn("width", img, img)
            self.assertIn("height", img, img)
            self.assertTrue((self.out / img["src"].lstrip("/")).exists(), img["src"])

    def test_below_the_fold_images_are_lazy(self):
        after_hero = self.html[self.html.index('id="features"'):]
        for src in re.findall(r"<img [^>]*>", after_hero):
            if "phone-screen" not in src and 'alt=""' not in src:
                self.assertIn('loading="lazy"', src)

    def test_no_third_party_requests_without_gtm_id(self):
        for script in self.page.scripts:
            self.assertTrue(script["src"].startswith("/assets/"))
        for style in self.page.styles:
            self.assertTrue(style["href"].startswith("/assets/"))
        self.assertNotRegex(self.html, r"googletagmanager|google-analytics|gtag\(|fonts\.googleapis")

    def test_no_banner_or_consent_script_without_gtm_id(self):
        self.assertNotIn('id="consent"', self.html)
        self.assertNotIn("data-consent-settings", self.html)
        self.assertNotIn("data-gtm-id", self.html)


class Consent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out, _, cls.html, cls.page = built({"GTM_ID": "GTM-T6TDXTK3", "PRIVACY_URL": "https://alondra1.com/privacy"})
        consent = next(s for s in cls.page.scripts if "/consent." in s["src"])
        cls.consent_tag = consent
        cls.code = (cls.out / consent["src"].lstrip("/")).read_text(encoding="utf-8")

    def test_no_google_script_in_markup(self):
        """gtm.js is injected only after the visitor accepts, never present in the HTML itself."""
        self.assertNotIn("googletagmanager", self.html)
        self.assertTrue(all(s["src"].startswith("/assets/") for s in self.page.scripts))

    def test_consent_script_runs_first_and_carries_the_id(self):
        self.assertEqual(self.consent_tag["data-gtm-id"], "GTM-T6TDXTK3")
        self.assertNotIn("async", self.consent_tag)
        self.assertNotIn("defer", self.consent_tag)
        self.assertEqual(self.page.scripts[0], self.consent_tag)

    def test_consent_mode_v2_defaults_denied(self):
        default = self.code[self.code.index('gtag("consent", "default"'):]
        default = default[:default.index("});")]
        for signal in ("ad_storage", "ad_user_data", "ad_personalization", "analytics_storage"):
            self.assertRegex(default, signal + r': "denied"')
        self.assertLess(self.code.index('gtag("consent", "default"'), self.code.index("googletagmanager.com/gtm.js"))

    def test_gtm_loads_only_on_grant(self):
        load = self.code.index("function loadGtm")
        self.assertEqual(len(re.findall(r"(?<!function )loadGtm\(\)", self.code)), 1,
                         "loadGtm() is called from grant() only")
        grant = self.code[self.code.index("function grant()"):]
        grant = grant[:grant.index("\n  }")]  # the function body only
        self.assertIn("loadGtm();", grant)
        self.assertIn('analytics_storage: "granted"', grant)
        self.assertNotRegex(grant, r"ad_storage|ad_user_data|ad_personalization",
                            "accepting analytics must not grant advertising signals")
        self.assertGreater(load, 0)

    def test_choice_not_stored_in_cookies(self):
        self.assertIn("localStorage", self.code)
        self.assertNotRegex(self.code, r'document\.cookie\s*=\s*name \+ "=[^;]')

    def test_banner_is_small_and_balanced(self):
        banner = self.html[self.html.index('id="consent"'):]
        banner = banner[:banner.index("</section>")]
        self.assertIn("hidden", self.html[self.html.index('<section class="consent"'):self.html.index('id="consent"') + 80])
        buttons = re.findall(r'<button class="([^"]+)" type="button" data-consent="(granted|denied)">', banner)
        self.assertEqual(sorted(b[1] for b in buttons), ["denied", "granted"])
        self.assertEqual(len({b[0] for b in buttons}), 1, "Accept and Decline must look the same")
        self.assertIn('href="https://alondra1.com/privacy"', banner)
        self.assertLess(len(re.sub(r"<[^>]+>", "", banner).split()), 20, "keep the banner text short")

    def test_banner_is_after_main_content(self):
        self.assertGreater(self.html.index('id="consent"'), self.html.index("</footer>"))

    def test_cookie_settings_in_footer(self):
        footer = self.html[self.html.index('<footer'):self.html.index('</footer>')]
        self.assertIn("data-consent-settings", footer)
        self.assertIn("Cookie settings", footer)

    def test_invalid_gtm_id_rejected(self):
        with self.assertRaises(build.ConfigError):
            build.load_config(env={"GTM_ID": "G-12345"})
        with self.assertRaises(build.ConfigError):
            build.load_config(env={"GTM_ID": "GTM-ABC\"><script>"})

    def test_csp_allows_gtm_hosts(self):
        csp = (build.ROOT / "nginx" / "snippets" / "security-headers.inc").read_text(encoding="utf-8")
        self.assertIn("script-src 'self' https://*.googletagmanager.com", csp)
        self.assertIn("https://*.google-analytics.com", csp)
        self.assertNotIn("unsafe-inline", csp)

    def test_fingerprinted_assets_exist(self):
        for path in [s["src"] for s in self.page.scripts] + [s["href"] for s in self.page.styles]:
            self.assertRegex(path, r"^/assets/[a-z]+\.[0-9a-f]{10}\.(css|js)$")
            self.assertTrue((self.out / path.lstrip("/")).exists())

    def test_no_free_cloud_sync_promise(self):
        self.assertIn("Cloud sync between devices is part of the Personal plan.", self.html)
        free_card = self.html[self.html.index('data-plan="free"'):self.html.index('data-plan="personal"')]
        self.assertNotIn("Cloud sync", free_card)
        self.assertNotIn("Archive", free_card)

    def test_404_page(self):
        self.assertIn("Page not found", (self.out / "404.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()


class EnvironmentVariants(unittest.TestCase):
    """One image, two variants: dev is hidden from search and analytics; prod is canonical, with consent-gated GTM."""

    @classmethod
    def setUpClass(cls):
        cls.dev_out, cls.dev_cfg, cls.dev, cls.dev_page = built(environment="dev")
        cls.prod_out, cls.prod_cfg, cls.prod, cls.prod_page = built(environment="prod", legal=COMPLETE_LEGAL)

    def test_dev_is_noindex_without_analytics(self):
        self.assertEqual(self.dev_page.meta.get("robots"), "noindex, nofollow")
        self.assertEqual((self.dev_out / "robots.txt").read_text(encoding="utf-8"), "User-agent: *\nDisallow: /\n")
        self.assertFalse((self.dev_out / "sitemap.xml").exists())
        self.assertNotIn("data-gtm-id", self.dev)
        self.assertNotIn("googletagmanager", self.dev)
        self.assertEqual(self.dev_page.meta["canonical"], "https://alondra1.dev/")

    def test_dev_links_point_to_dev(self):
        hrefs = [link.get("href", "") for link in self.dev_page.links]
        self.assertIn("https://api.alondra1.dev/account/", hrefs)
        self.assertFalse(any("://api.alondra1.com" in h or "://app.alondra1.com" in h for h in hrefs))

    def test_prod_is_canonical_indexable_with_consent_gated_gtm(self):
        self.assertNotIn("robots", self.prod_page.meta)
        self.assertEqual(self.prod_page.meta["canonical"], "https://alondra1.com/")
        self.assertIn("Sitemap: https://alondra1.com/sitemap.xml", (self.prod_out / "robots.txt").read_text(encoding="utf-8"))
        self.assertIn('data-gtm-id="GTM-T6TDXTK3"', self.prod)
        self.assertNotIn("googletagmanager.com/gtm.js", self.prod)  # loaded by consent.js only after Accept

    def test_prod_never_names_a_dev_host(self):
        self.assertNotIn("alondra1.dev", self.prod)
        with self.assertRaises(build.ConfigError):
            bad = copy.deepcopy(CONFIG)
            bad["environments"]["prod"]["links"]["login"] = "https://api.alondra1.dev/account/"
            path = Path(tempfile.mkdtemp()) / "site.json"
            path.write_text(json.dumps(bad), encoding="utf-8")
            build.load_config(path, env={}, environment="prod")

    def test_dev_never_uses_a_prod_site_url(self):
        bad = copy.deepcopy(CONFIG)
        bad["environments"]["dev"]["siteUrl"] = "https://alondra1.com"
        path = Path(tempfile.mkdtemp()) / "site.json"
        path.write_text(json.dumps(bad), encoding="utf-8")
        with self.assertRaises(build.ConfigError):
            build.load_config(path, env={}, environment="dev")

    def test_web_app_button_only_when_enabled(self):
        self.assertNotIn("Open Web App", self.prod)
        enabled = copy.deepcopy(CONFIG)
        enabled["webApp"]["enabled"] = True
        path = Path(tempfile.mkdtemp()) / "site.json"
        path.write_text(json.dumps(enabled), encoding="utf-8")
        cfg = build.load_config(path, env={}, environment="prod")
        self.assertIn('href="https://app.alondra1.com/"', build.web_app_cta(cfg))

    def test_dev_is_labelled_as_the_development_and_test_version(self):
        self.assertIn('class="env-banner"', self.dev)
        self.assertIn("Development and test version", self.dev)
        self.assertNotIn("env-banner", self.prod)

    def test_dev_opens_the_dev_web_app_and_prod_does_not_inherit_it(self):
        self.assertIn('href="https://app.alondra1.dev/"', build.web_app_cta(self.dev_cfg))
        web = next(p for p in self.dev_cfg["platforms"] if p["id"] == "web")
        self.assertEqual((web["status"], web["downloadUrl"]), ("available", "https://app.alondra1.dev/"))
        self.assertIn('aria-label="Open the Alondra1 Web app"', self.dev)
        self.assertNotIn("Open Web App", self.prod)
        self.assertTrue(all(p["status"] != "available" for p in self.prod_cfg["platforms"]))
        # Dev downloads are public (owner decision 2026-11-26): the rolling dev-latest prereleases.
        for pid, url in (("windows", "alondra1-windows/releases/download/dev-latest/Alondra1-dev-setup.exe"),
                         ("android", "alondra1-android/releases/download/dev-latest/Alondra1-dev.apk")):
            p = next(p for p in self.dev_cfg["platforms"] if p["id"] == pid)
            self.assertEqual(p["status"], "available")
            self.assertTrue(p["downloadUrl"].endswith(url))
        # Apps without a verified download stay "coming soon" on dev too.
        self.assertTrue(all(p["status"] == "comingSoon" for p in self.dev_cfg["platforms"] if p["id"] in ("macos", "ios", "tablet")))

    def test_environment_platform_overrides_are_validated(self):
        bad = copy.deepcopy(CONFIG)
        bad["environments"]["dev"]["platforms"] = {"android": {"status": "available"}}  # no download URL
        path = Path(tempfile.mkdtemp()) / "site.json"
        path.write_text(json.dumps(bad), encoding="utf-8")
        with self.assertRaises(build.ConfigError):
            build.load_config(path, env={}, environment="dev")

    def test_cli_builds_both_variants(self):
        out = Path(tempfile.mkdtemp()) / "dist"
        self.assertEqual(build.main(["--out", str(out)]), 0)
        self.assertTrue((out / "dev" / "index.html").exists() and (out / "prod" / "index.html").exists())


class FourPlansAndPlatformLimits(unittest.TestCase):
    def test_four_plans_paid_disabled_without_prices(self):
        _, _, html, page = built(environment="prod")
        self.assertEqual([p["id"] for p in CONFIG["plans"]], ["free", "personal", "family", "enterprise"])
        for plan_id in ("personal", "family", "enterprise"):
            self.assertIn(f'data-plan="{plan_id}"', html)
        self.assertEqual(sum(1 for b in page.buttons if "disabled" in b), 3)
        self.assertIsNone(re.search(r"[$€£]\s?\d", html), "no prices before owner approval")

    def test_android_and_web_do_not_claim_mail_or_contacts(self):
        for platform in CONFIG["platforms"]:
            if platform["id"] != "windows":
                self.assertNotIn("Mail", platform.get("modules", []))
                self.assertNotIn("Contacts", platform.get("modules", []))
        bad = copy.deepcopy(CONFIG)
        bad["platforms"][2]["modules"] = ["To-do", "Mail"]
        bad.pop("environments", None)
        with self.assertRaises(build.ConfigError):
            build.validate(bad)

    def test_platform_limitations_are_stated(self):
        _, _, html, _ = built(environment="prod")
        self.assertIn("Mail and Contacts are in the Windows app.", html)


class ServingConfig(unittest.TestCase):
    """nginx serves the variant named by ALONDRA1_ENVIRONMENT; dev adds X-Robots-Tag in every location."""

    def test_template_selects_the_variant(self):
        template = (build.ROOT / "nginx" / "templates" / "default.conf.template").read_text(encoding="utf-8")
        self.assertIn("root /usr/share/nginx/html/${ALONDRA1_ENVIRONMENT};", template)
        locations = template.count("location ")
        self.assertEqual(template.count("env-${ALONDRA1_ENVIRONMENT}.inc"), template.count("security-headers.inc"))
        self.assertGreaterEqual(locations, 4)

    def test_dev_headers_noindex(self):
        dev = (build.ROOT / "nginx" / "snippets" / "env-dev.inc").read_text(encoding="utf-8")
        self.assertIn('X-Robots-Tag "noindex, nofollow" always', dev)
        self.assertNotIn("X-Robots-Tag", (build.ROOT / "nginx" / "snippets" / "env-prod.inc").read_text(encoding="utf-8"))

    def test_entrypoint_refuses_unknown_environment(self):
        script = (build.ROOT / "nginx" / "05-alondra1-environment.sh").read_text(encoding="utf-8")
        self.assertIn("dev|prod)", script)
        self.assertIn("exit 1", script)
