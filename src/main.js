// Alondra1 landing: mobile menu, header state, footer year. Analytics (if enabled) is loaded separately by build.py.
(function () {
  "use strict";
  var root = document.documentElement;
  root.classList.remove("no-js");
  root.classList.add("js");

  document.addEventListener("DOMContentLoaded", function () {
    var header = document.querySelector(".site-header");
    var toggle = document.querySelector(".menu-toggle");
    var nav = document.getElementById("primary-nav");
    var desktop = window.matchMedia("(min-width: 1024px)");

    function isOpen() {
      return toggle.getAttribute("aria-expanded") === "true";
    }

    function setOpen(open, returnFocus) {
      toggle.setAttribute("aria-expanded", String(open));
      toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
      nav.classList.toggle("is-open", open);
      if (open) {
        var first = nav.querySelector("a, button");
        if (first) first.focus();
      } else if (returnFocus) {
        toggle.focus();
      }
    }

    if (toggle && nav) {
      toggle.addEventListener("click", function () {
        setOpen(!isOpen(), true);
      });

      // Close after choosing a destination, on Escape, and on a click or tap outside the menu.
      nav.addEventListener("click", function (event) {
        if (event.target.closest("a") && isOpen()) setOpen(false, false);
      });
      document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && isOpen()) setOpen(false, true);
      });
      document.addEventListener("click", function (event) {
        if (isOpen() && !nav.contains(event.target) && !toggle.contains(event.target)) setOpen(false, false);
      });
      // Keep keyboard focus inside the open menu (Tab past the last link returns to the toggle).
      nav.addEventListener("keydown", function (event) {
        if (event.key !== "Tab" || !isOpen()) return;
        var items = nav.querySelectorAll("a, button");
        var last = items[items.length - 1];
        if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          toggle.focus();
        }
      });
      var onBreakpoint = function () {
        if (desktop.matches && isOpen()) setOpen(false, false);
      };
      if (desktop.addEventListener) desktop.addEventListener("change", onBreakpoint);
      else if (desktop.addListener) desktop.addListener(onBreakpoint);
    }

    if (header) {
      var onScroll = function () {
        header.classList.toggle("is-scrolled", window.scrollY > 4);
      };
      window.addEventListener("scroll", onScroll, { passive: true });
      onScroll();
    }

    var year = document.querySelector("[data-year]");
    if (year) year.textContent = String(new Date().getFullYear());
  });
})();
