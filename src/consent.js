// Cookie consent + Google Consent Mode v2 (basic implementation) for the Alondra1 landing page.
//
// - Every consent signal defaults to "denied" before any Google code exists on the page.
// - Google Tag Manager (and therefore GA4) is not even requested until the visitor accepts:
//   before consent there are no requests to Google and no cookies.
// - Accept grants analytics_storage only; ad_storage, ad_user_data and ad_personalization stay denied.
// - The choice is stored in localStorage (strictly necessary, no cookie) for 12 months, then asked again.
// - "Cookie settings" in the footer reopens the banner; declining after accepting deletes the _ga cookies
//   and reloads the page so the already-running container stops.
//
// Loaded synchronously in <head> with data-gtm-id; inline scripts are blocked by the CSP.
(function () {
  "use strict";
  var script = document.currentScript;
  var GTM_ID = script && script.getAttribute("data-gtm-id");
  var KEY = "alondra1-consent";
  var VERSION = 1;
  var MAX_AGE_MS = 365 * 24 * 60 * 60 * 1000;

  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }
  window.gtag = gtag;

  gtag("consent", "default", {
    ad_storage: "denied",
    ad_user_data: "denied",
    ad_personalization: "denied",
    analytics_storage: "denied",
    functionality_storage: "denied",
    personalization_storage: "denied",
    security_storage: "granted"
  });
  gtag("set", "ads_data_redaction", true);
  gtag("set", "url_passthrough", false);

  function readChoice() {
    try {
      var raw = window.localStorage.getItem(KEY);
      if (!raw) return null;
      var data = JSON.parse(raw);
      if (data.v !== VERSION || !data.ts || Date.now() - data.ts > MAX_AGE_MS) return null;
      return data.analytics === "granted" || data.analytics === "denied" ? data.analytics : null;
    } catch (e) {
      return null; // storage blocked: ask again, track nothing
    }
  }

  function saveChoice(value) {
    try {
      window.localStorage.setItem(KEY, JSON.stringify({ v: VERSION, analytics: value, ts: Date.now() }));
    } catch (e) { /* the choice still applies to this page view */ }
  }

  var gtmLoaded = false;
  function loadGtm() {
    if (gtmLoaded || !GTM_ID) return;
    gtmLoaded = true;
    gtag("js", new Date());
    window.dataLayer.push({ "gtm.start": new Date().getTime(), event: "gtm.js" });
    var s = document.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtm.js?id=" + encodeURIComponent(GTM_ID);
    document.head.appendChild(s);
  }

  function grant() {
    gtag("consent", "update", { analytics_storage: "granted" });
    loadGtm();
  }

  function deleteAnalyticsCookies() {
    var host = window.location.hostname;
    var domains = ["", host, "." + host, "." + host.split(".").slice(-2).join(".")];
    document.cookie.split(";").forEach(function (part) {
      var name = part.split("=")[0].trim();
      if (!/^(_ga|_gid|_gat|_gcl)/.test(name)) return;
      domains.forEach(function (d) {
        document.cookie = name + "=; Max-Age=0; path=/" + (d ? "; domain=" + d : "");
      });
    });
  }

  var choice = readChoice();
  if (choice === "granted") grant();

  document.addEventListener("DOMContentLoaded", function () {
    var banner = document.getElementById("consent");
    if (!banner) return;

    function show() {
      banner.hidden = false;
    }
    function hide() {
      banner.hidden = true;
    }

    banner.addEventListener("click", function (event) {
      var button = event.target.closest("[data-consent]");
      if (!button) return;
      var value = button.getAttribute("data-consent");
      var previous = readChoice();
      saveChoice(value);
      hide();
      if (value === "granted") {
        grant();
      } else {
        gtag("consent", "update", { analytics_storage: "denied" });
        deleteAnalyticsCookies();
        if (gtmLoaded || previous === "granted") window.location.reload();
      }
    });

    var settings = document.querySelector("[data-consent-settings]");
    if (settings) {
      settings.hidden = false;
      settings.addEventListener("click", function () {
        show();
        var first = banner.querySelector("button");
        if (first) first.focus();
      });
    }

    if (choice === null) show();
  });
})();
