"""Build the Alondra1 landing page into static folders, one per environment.

Standard library only. Content data lives in config/site.json; each environment (dev, prod) overlays its site URL,
links, analytics and indexing rules. One image carries both variants and nginx serves the one named by
ALONDRA1_ENVIRONMENT, so prod runs exactly the image that passed in dev. Environment variables (SITE_URL, LOGIN_URL,
REGISTER_URL, PRIVACY_URL, TERMS_URL, CONTACT_URL, GTM_ID) still override values for local builds.

    python build.py                    # -> dist/dev and dist/prod
    python build.py --env prod         # -> dist/ (one variant)
    python build.py --out /dist        # Docker build stage
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config" / "site.json"
TEMPLATE = ROOT / "src" / "index.html"
STATIC = ROOT / "src"  # styles.css, main.js
PUBLIC = ROOT / "public"  # copied as-is

CORE_FREE_APPS = ("To-do", "Mail", "Calendar", "Notes", "Contacts")
PAID_ONLY_FEATURES = ("Cloud sync", "Archive")
PLATFORM_IDS = ("windows", "macos", "android", "ios", "tablet", "web")
ENVIRONMENTS = ("dev", "prod")
# Mail and Contacts exist only in the Windows app; no other platform may claim them (spec v1.1 section 9).
WINDOWS_ONLY_MODULES = ("Mail", "Contacts")
PLATFORM_STATUSES = ("available", "comingSoon", "notSupported")
LINK_ENV = {
    "login": "LOGIN_URL",
    "register": "REGISTER_URL",
    "privacy": "PRIVACY_URL",
    "terms": "TERMS_URL",
    "contact": "CONTACT_URL",
}


class ConfigError(ValueError):
    pass


# ---------------------------------------------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------------------------------------------

def load_config(path: Path = CONFIG, env: dict[str, str] | None = None, environment: str | None = None) -> dict:
    env = os.environ if env is None else env
    config = json.loads(path.read_text(encoding="utf-8"))
    config.pop("$comment", None)
    environments = config.pop("environments", {})
    config["environment"] = environment or "local"
    config["noindex"] = False
    config["webAppUrl"] = ""
    gtm_default = ""
    if environment is not None:
        if environment not in ENVIRONMENTS or environment not in environments:
            raise ConfigError(f"unknown environment {environment!r}")
        overlay = environments[environment]
        config["siteUrl"] = overlay["siteUrl"]
        config["links"] = dict(overlay["links"])
        config["noindex"] = bool(overlay["noindex"])
        config["webAppUrl"] = overlay.get("webAppUrl", "")
        gtm_default = overlay.get("gtmId", "")
    if env.get("SITE_URL"):
        config["siteUrl"] = env["SITE_URL"]
    for key, var in LINK_ENV.items():
        if env.get(var) is not None and env.get(var) != "":
            config["links"][key] = env[var].strip()
    # Google Tag Manager: from the environment (prod only) or GTM_ID; never in a noindex (dev) variant.
    config["gtmId"] = (env.get("GTM_ID") or gtm_default).strip()
    if config["noindex"]:
        config["gtmId"] = ""
    validate(config)
    return config


def is_external_url(value: str) -> bool:
    return value.startswith("https://") or value.startswith("mailto:")


def is_valid_link(value: str) -> bool:
    """A link may be an https/mailto URL, a site path, or an on-page anchor. Plain http is refused."""
    return is_external_url(value) or value.startswith("/") or bool(re.fullmatch(r"#[a-z][a-z0-9-]*", value))


def validate(config: dict) -> None:
    site = config.get("siteUrl", "")
    if not re.fullmatch(r"https://[a-z0-9.-]+", site):
        raise ConfigError(f"siteUrl must be an https origin without a trailing slash, got {site!r}")

    for key, value in config["links"].items():
        if key not in LINK_ENV:
            raise ConfigError(f"unknown link {key!r}")
        if value and not is_valid_link(value):
            raise ConfigError(f"links.{key} must be https://, mailto:, /path or #anchor, got {value!r}")

    environment = config.get("environment", "local")
    web = config.get("webApp", {"enabled": False})
    if web.get("enabled") and environment != "local" and not config.get("webAppUrl", "").startswith("https://"):
        raise ConfigError("webApp.enabled needs an https webAppUrl for the environment")
    if environment == "dev" and not config["siteUrl"].endswith("dev.alondra1.com"):
        raise ConfigError("the dev variant must use a dev hostname")
    if environment == "prod" and (
            "dev." in config["siteUrl"] or "dev." in config.get("webAppUrl", "")
            or any("dev." in value for value in config["links"].values())):
        raise ConfigError("the prod variant must not contain a dev hostname")
    if config.get("gtmId") and not re.fullmatch(r"GTM-[A-Z0-9]{4,12}", config["gtmId"]):
        raise ConfigError(f"GTM_ID must look like GTM-XXXXXXX, got {config['gtmId']!r}")

    plans = config["plans"]
    fields = {"id", "name", "priceLabel", "periodLabel", "description", "features", "ctaLabel", "ctaUrl",
              "featured", "enabled"}
    ids = [p.get("id") for p in plans]
    if len(set(ids)) != len(ids):
        raise ConfigError("plan ids must be unique")
    for plan in plans:
        missing = fields - plan.keys()
        if missing:
            raise ConfigError(f"plan {plan.get('id')!r} misses {sorted(missing)}")
        if plan["enabled"] and not (plan["ctaUrl"] and is_valid_link(plan["ctaUrl"])):
            raise ConfigError(f"plan {plan['id']!r} is enabled but has no valid ctaUrl")
    free = next((p for p in plans if p["id"] == "free"), None)
    if free is None:
        raise ConfigError("a 'free' plan is required")
    for app in CORE_FREE_APPS:
        if app not in free["features"]:
            raise ConfigError(f"the free plan must include {app}")
    for plan in plans:
        for feature in PAID_ONLY_FEATURES:
            if plan["id"] == "free" and feature in plan["features"]:
                raise ConfigError(f"{feature} is a paid feature and cannot be in the free plan")
    paid = [p for p in plans if p["id"] != "free"]
    for plan in paid:
        for feature in PAID_ONLY_FEATURES:
            if feature not in plan["features"]:
                raise ConfigError(f"paid plan {plan['id']!r} must list {feature}")
        for app in CORE_FREE_APPS:
            if app in plan["features"]:
                raise ConfigError(f"paid plan {plan['id']!r} must not gate {app}; use 'Everything in Free'")

    platforms = config["platforms"]
    if [p.get("id") for p in platforms] != list(PLATFORM_IDS):
        raise ConfigError(f"platforms must be exactly {list(PLATFORM_IDS)} in this order")
    for platform in platforms:
        status = platform.get("status")
        if status not in PLATFORM_STATUSES:
            raise ConfigError(f"platform {platform['id']!r} has invalid status {status!r}")
        if platform["id"] != "windows":
            for module in WINDOWS_ONLY_MODULES:
                if module in platform.get("modules", []):
                    raise ConfigError(f"platform {platform['id']!r} must not list {module} (Windows only)")
        url = platform.get("downloadUrl", "")
        if status == "available":
            if not url.startswith("https://"):
                raise ConfigError(f"platform {platform['id']!r} is available but has no https downloadUrl")
        elif url:
            raise ConfigError(f"platform {platform['id']!r} is {status}; remove its downloadUrl")


# ---------------------------------------------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------------------------------------------

def esc(value: str) -> str:
    return html.escape(value, quote=True)


# Line icons in one style (24 x 24, 1.75 stroke, round caps), drawn for this site.
ICONS = {
    "zap": '<path d="M13 3 5 14h6l-1 7 8-11h-6l1-7Z"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    "list": '<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r="1"/><circle cx="4.5" cy="12" r="1"/><circle cx="4.5" cy="18" r="1"/>',
    "target": '<circle cx="12" cy="12" r="9"/><path d="m8.5 12 2.5 2.5 4.5-5"/>',
    "check": '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    "todo": '<rect x="3.5" y="4" width="17" height="16" rx="3"/><path d="m7.5 10 1.8 1.8 3.2-3.3M14.5 10.5h3M7.5 15.5h10"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="m4 7 8 6 8-6"/>',
    "calendar": '<rect x="3.5" y="5" width="17" height="15.5" rx="2.5"/><path d="M8 3v4M16 3v4M3.5 10h17"/><path d="M8 14h.01M12 14h.01M16 14h.01M8 17.5h.01M12 17.5h.01"/>',
    "notes": '<path d="M14 3H7a2.5 2.5 0 0 0-2.5 2.5v13A2.5 2.5 0 0 0 7 21h10a2.5 2.5 0 0 0 2.5-2.5V8.5L14 3Z"/><path d="M14 3v5.5h5.5M8.5 13h7M8.5 16.5h5"/>',
    "contacts": '<circle cx="12" cy="8.5" r="4"/><path d="M4.5 20.5a7.5 7.5 0 0 1 15 0"/>',
    "monitor": '<rect x="3" y="4" width="18" height="12.5" rx="2"/><path d="M8.5 20.5h7M12 16.5v4"/>',
    "laptop": '<rect x="4.5" y="5" width="15" height="10.5" rx="1.5"/><path d="M2.5 19h19"/>',
    "phone": '<rect x="6.5" y="2.5" width="11" height="19" rx="2.5"/><path d="M11 18.5h2"/>',
    "tablet": '<rect x="4" y="2.5" width="16" height="19" rx="2.5"/><path d="M11 18.5h2"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "star": '<path d="m12 3.5 2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8-4.3-4.1 5.9-.9L12 3.5Z"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7.5V12l3 2"/>',
    "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
    "close": '<path d="M6 6l12 12M18 6 6 18"/>',
    "lock": '<rect x="5" y="10.5" width="14" height="10" rx="2"/><path d="M8.5 10.5V7.5a3.5 3.5 0 0 1 7 0v3"/>',
}


def icon(name: str, cls: str = "icon", size: int = 24) -> str:
    return (f'<svg class="{cls}" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" '
            f'focusable="false">{ICONS[name]}</svg>')


def link_attrs(url: str) -> str:
    """External links open in the same tab; mail links and paths stay plain."""
    return f'href="{esc(url)}"'


# ---------------------------------------------------------------------------------------------------------------
# Phone mockup (concept): a phone-native to-do screen styled after the real dark Windows To-do UI.
# It is an illustration, not a screenshot of a released mobile app.
# ---------------------------------------------------------------------------------------------------------------

PHONE_SCREENS = {
    "myday": {
        "title": "My Day",
        "subtitle": "Saturday, November 21",
        "icon": "sun",
        "count": "3 open",
        "tasks": [
            {"title": "Book the dentist appointment", "meta": "Personal", "when": "Today 16:00", "star": True},
            {"title": "Buy groceries for the weekend", "meta": "Groceries", "when": "Today", "progress": "2 of 5",
             "accent": True},
            {"title": "Water the balcony plants", "meta": "Home", "when": "Today"},
            {"title": "Call Grandma", "meta": "Personal", "done": True},
        ],
        "add": "Add a task",
    },
    "groceries": {
        "title": "Groceries",
        "subtitle": "Personal list",
        "icon": "list",
        "count": "4 open",
        "tasks": [
            {"title": "Oat milk", "meta": "Groceries"},
            {"title": "Fresh basil", "meta": "Groceries", "star": True},
            {"title": "Coffee beans", "meta": "Groceries"},
            {"title": "Bread", "meta": "Groceries", "done": True},
        ],
        "add": "Add an item",
    },
}


M_DOT = '<span class="m-dot">·</span>'


def phone(screen: str, label: str, size: str = "lg") -> str:
    data = PHONE_SCREENS[screen]
    rows = []
    for task in data["tasks"]:
        classes = ["m-task"]
        if task.get("done"):
            classes.append("is-done")
        if task.get("accent"):
            classes.append("has-accent")
        meta = [f'<span>{esc(task["meta"])}</span>']
        if task.get("when"):
            meta.append(f'<span class="m-when">{icon("calendar", "m-ico", 12)}{esc(task["when"])}</span>')
        if task.get("progress"):
            meta.append(f'<span class="m-progress"><span class="m-bar"><span></span></span>{esc(task["progress"])}</span>')
        star = icon("star", "m-star is-on" if task.get("star") else "m-star", 18)
        check = icon("check", "m-check-mark", 12) if task.get("done") else ""
        rows.append(
            f'<li class="{" ".join(classes)}"><span class="m-check">{check}</span>'
            f'<span class="m-body"><span class="m-title">{esc(task["title"])}</span>'
            f'<span class="m-meta">{M_DOT.join(meta)}</span></span>{star}</li>'
        )
    return f"""<figure class="phone phone--{size}" data-concept="mobile-ui">
  <div class="phone-frame" role="img" aria-label="{esc(label)}">
    <div class="phone-screen" aria-hidden="true">
      <div class="m-status"><span>9:41</span><span class="m-island"></span><span class="m-signal"><i></i><i></i><i></i></span></div>
      <div class="m-top">
        <img src="/images/alondra1-logo-96.png" alt="" width="22" height="22">
        <span class="m-app">Alondra1</span>
        <span class="m-avatar">A</span>
      </div>
      <div class="m-head">
        {icon(data["icon"], "m-head-ico", 26)}
        <div><p class="m-h1">{esc(data["title"])}</p><p class="m-sub">{esc(data["subtitle"])}</p></div>
        <span class="m-count">{esc(data["count"])}</span>
      </div>
      <ul class="m-list">{"".join(rows)}</ul>
      <div class="m-add">{icon("plus", "m-ico", 16)}<span>{esc(data["add"])}</span></div>
      <div class="m-tabs"><span class="is-active">{icon("sun", "m-ico", 18)}My Day</span><span>{icon("star", "m-ico", 18)}Important</span><span>{icon("calendar", "m-ico", 18)}Planned</span><span>{icon("list", "m-ico", 18)}Lists</span></div>
    </div>
  </div>
</figure>"""


# ---------------------------------------------------------------------------------------------------------------
# Sections generated from data
# ---------------------------------------------------------------------------------------------------------------

def auth_links(config: dict, where: str) -> str:
    """Log in and Register appear only when a verified destination is configured (no dead buttons)."""
    out = []
    links = config["links"]
    if links["login"]:
        out.append(f'<a class="nav-link {where}-login" {link_attrs(links["login"])}>Log in</a>')
    if links["register"]:
        out.append(f'<a class="button button--ghost button--sm {where}-register" {link_attrs(links["register"])}>Register</a>')
    return "\n".join(out)


def secondary_cta(config: dict) -> str:
    url = config["links"]["register"]
    return f'<a class="button button--ghost" {link_attrs(url)}>Create account</a>' if url else ""


def web_app_cta(config: dict) -> str:
    """The Web app button appears only once the Web app is verified (webApp.enabled) for this environment."""
    web = config.get("webApp", {})
    if not web.get("enabled") or not config.get("webAppUrl"):
        return ""
    return f'<a class="button button--secondary" {link_attrs(config["webAppUrl"])}>{esc(web.get("label", "Open Web App"))}</a>'


def robots_meta(config: dict) -> str:
    return '<meta name="robots" content="noindex, nofollow">' if config.get("noindex") else ""


def plans_note(config: dict) -> str:
    note = config.get("plansNote", "")
    return f'<p class="plans-note">{esc(note)}</p>' if note else ""


def plans_html(config: dict) -> str:
    cards = []
    for plan in config["plans"]:
        featured = " plan--featured" if plan["featured"] else ""
        is_free = plan["id"] == "free"
        items = []
        for feature in plan["features"]:
            items.append(f'<li>{icon("check", "plan-check", 18)}<span>{esc(feature)}</span></li>')
        period = f'<span class="plan-period">{esc(plan["periodLabel"])}</span>' if plan["periodLabel"] else ""
        price_cls = "plan-price" if is_free or plan["enabled"] else "plan-price plan-price--pending"
        if plan["enabled"]:
            cta = (f'<a class="button {"button--primary" if plan["featured"] else "button--secondary"} button--block" '
                   f'{link_attrs(plan["ctaUrl"])}>{esc(plan["ctaLabel"])}</a>')
            note = ""
        else:
            cta = (f'<button class="button button--secondary button--block" type="button" disabled '
                   f'aria-describedby="plan-{esc(plan["id"])}-note">{esc(plan["ctaLabel"])}</button>')
            note = (f'<p class="plan-note" id="plan-{esc(plan["id"])}-note">{icon("clock", "icon icon--sm", 16)}'
                    f'Not available yet. The free plan works without it.</p>')
        badge = '<span class="plan-badge">Cloud sync + Archive</span>' if not is_free else '<span class="plan-badge plan-badge--free">Free core apps</span>'
        cards.append(f"""<article class="plan{featured}" data-plan="{esc(plan["id"])}">
  <header class="plan-head">{badge}<h3>{esc(plan["name"])}</h3><p class="plan-desc">{esc(plan["description"])}</p></header>
  <p class="{price_cls}">{esc(plan["priceLabel"])}{period}</p>
  <ul class="plan-features">{"".join(items)}</ul>
  {cta}
  {note}
</article>""")
    return "\n".join(cards)


STATUS_TEXT = {"available": "Available", "comingSoon": "Coming soon", "notSupported": "Not available"}
PLATFORM_ICON = {"windows": "monitor", "macos": "laptop", "android": "phone", "ios": "phone", "tablet": "tablet",
                 "web": "monitor"}


def platforms_html(config: dict) -> str:
    cards = []
    for p in config["platforms"]:
        status = p["status"]
        subtitle = f'<span class="platform-sub">{esc(p["subtitle"])}</span>' if p.get("subtitle") else ""
        if p.get("modules"):
            subtitle += f'<span class="platform-modules">{esc(", ".join(p["modules"]))}</span>'
        if status == "available":
            action = (f'<a class="button button--primary button--sm" {link_attrs(p["downloadUrl"])} '
                      f'aria-label="Download Alondra1 for {esc(p["label"])}">Download</a>')
        else:
            action = f'<span class="status status--{esc(status)}">{STATUS_TEXT[status]}</span>'
        cards.append(f"""<li class="platform platform--{esc(status)}" data-platform="{esc(p["id"])}" data-status="{esc(status)}">
  <span class="platform-icon">{icon(PLATFORM_ICON[p["id"]], "icon", 28)}</span>
  <span class="platform-text"><span class="platform-name">{esc(p["label"])}</span>{subtitle}</span>
  {action}
</li>""")
    return "\n".join(cards)


def footer_links(config: dict) -> str:
    links = config["links"]
    items = [(label, links[key]) for key, label in (("privacy", "Privacy"), ("terms", "Terms"), ("contact", "Contact"))
             if links[key]]
    return "".join(f'<li><a {link_attrs(url)}>{label}</a></li>' for label, url in items)


# ---------------------------------------------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------------------------------------------

def fingerprint(src: Path, out_dir: Path) -> str:
    data = src.read_bytes()
    digest = hashlib.sha256(data).hexdigest()[:10]
    name = f"{src.stem}.{digest}{src.suffix}"
    (out_dir / "assets").mkdir(parents=True, exist_ok=True)
    (out_dir / "assets" / name).write_bytes(data)
    return f"/assets/{name}"


def analytics_tags(config: dict, out_dir: Path) -> str:
    """The consent script (Consent Mode v2 defaults, then GTM only after the visitor accepts).

    Empty when no container id is configured: no banner, no Google code at all.
    """
    gtm = config.get("gtmId")
    if not gtm:
        return ""
    src = fingerprint(STATIC / "consent.js", out_dir)
    return f'<script src="{src}" data-gtm-id="{esc(gtm)}"></script>'


def consent_banner(config: dict) -> str:
    """Small, non-blocking banner. Accept and Decline look the same: refusing is as easy as agreeing."""
    if not config.get("gtmId"):
        return ""
    privacy = config["links"]["privacy"]
    more = f' <a {link_attrs(privacy)}>Privacy</a>' if privacy else ""
    return f"""<section class="consent" id="consent" aria-label="Cookie consent" hidden>
    <p class="consent-text">We use analytics cookies only if you agree.{more}</p>
    <div class="consent-actions">
      <button class="consent-btn" type="button" data-consent="denied">Decline</button>
      <button class="consent-btn" type="button" data-consent="granted">Accept</button>
    </div>
  </section>"""


def cookie_settings(config: dict) -> str:
    """Footer control to change the choice later (shown by consent.js; hidden without JavaScript)."""
    if not config.get("gtmId"):
        return ""
    return '<button class="footer-button" type="button" data-consent-settings hidden>Cookie settings</button>'


def render(config: dict, css: str, js: str, year: int, analytics: str = "") -> str:
    page = TEMPLATE.read_text(encoding="utf-8")
    values = {
        "ANALYTICS": analytics,
        "SITE_URL": esc(config["siteUrl"]),
        "CSS": css,
        "JS": js,
        "YEAR": str(year),
        "AUTH_DESKTOP": auth_links(config, "header"),
        "AUTH_MENU": auth_links(config, "menu"),
        "SECONDARY_CTA": secondary_cta(config),
        "WEB_APP_CTA": web_app_cta(config),
        "ROBOTS_META": robots_meta(config),
        "PLANS_NOTE": plans_note(config),
        "HERO_PHONE": phone("myday", "Illustration of the Alondra1 mobile to-do app showing My Day with four personal tasks"),
        "SHOWCASE_PHONE": phone("groceries", "Illustration of the Alondra1 mobile to-do app showing a groceries list", "md"),
        "PLANS": plans_html(config),
        "PLATFORMS": platforms_html(config),
        "FOOTER_LINKS": footer_links(config),
        "CONSENT_BANNER": consent_banner(config),
        "COOKIE_SETTINGS": cookie_settings(config),
    }
    values.update({f"ICON_{name.upper()}": icon(name) for name in ICONS})

    def replace(match: re.Match) -> str:
        key = match.group(1)
        if key not in values:
            raise KeyError(f"template placeholder {{{{{key}}}}} has no value")
        return values[key]

    page = re.sub(r"\{\{\s*([A-Z0-9_]+)\s*\}\}", replace, page)
    # Empty placeholders leave indentation behind: no trailing whitespace in the output.
    return re.sub(r"[ \t]+$", "", page, flags=re.MULTILINE)


def build(out: Path, env: dict[str, str] | None = None, year: int | None = None, environment: str | None = None) -> dict:
    config = load_config(env=env, environment=environment)
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(PUBLIC, out)
    css = fingerprint(STATIC / "styles.css", out)
    js = fingerprint(STATIC / "main.js", out)
    year = year or _dt.date.today().year
    analytics = analytics_tags(config, out)
    (out / "index.html").write_text(render(config, css, js, year, analytics), encoding="utf-8", newline="\n")

    site = config["siteUrl"]
    if config["noindex"]:
        # dev and other non-public variants: keep crawlers out entirely (nginx adds X-Robots-Tag as well).
        (out / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8", newline="\n")
    else:
        (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {site}/sitemap.xml\n",
                                        encoding="utf-8", newline="\n")
        (out / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"  <url><loc>{site}/</loc></url>\n"
            "</urlset>\n", encoding="utf-8", newline="\n")
    not_found = (ROOT / "src" / "404.html").read_text(encoding="utf-8").replace("{{CSS}}", css)
    (out / "404.html").write_text(not_found, encoding="utf-8", newline="\n")

    missing = [k for k in ("login", "register") if not config["links"][k]]
    if missing:
        print(f"note: {', '.join(missing)} URL not configured; the matching buttons are hidden", file=sys.stderr)
    return config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ROOT / "dist")
    parser.add_argument("--env", choices=ENVIRONMENTS, help="build one variant into --out (default: every variant)")
    args = parser.parse_args(argv)
    try:
        if args.env:
            build(args.out, environment=args.env)
            print(f"built {args.out} ({args.env})")
        else:
            if args.out.exists():
                shutil.rmtree(args.out)
            for environment in ENVIRONMENTS:
                build(args.out / environment, environment=environment)
                print(f"built {args.out / environment}")
    except ConfigError as error:
        print(f"config error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
