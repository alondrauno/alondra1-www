<p align="center"><img src="site/images/alondra1-banner.png" alt="Alondra1: local-first mail, calendar, and to-do for Windows" width="880"></p>

# Alondra1 website

[![ci](https://github.com/nikita4sea/alondra1-www/actions/workflows/ci.yml/badge.svg)](https://github.com/nikita4sea/alondra1-www/actions/workflows/ci.yml)

The public landing page for Alondra1: a static, dependency-free HTML and CSS site in [`site/`](site), published to GitHub Pages.

## Preview locally

Any static file server works, for example:

```sh
python -m http.server 8000 --directory site
```

Then open <http://localhost:8000>.

## Layout

| Path | Contents |
| --- | --- |
| `site/index.html` | The page. Text follows the product README in alondra1-windows. |
| `site/styles.css` | Styles; colors are the Alondra1 tokens from the Windows UI design (light and dark). |
| `site/images/` | Logo, banner, and screenshots copied from alondra1-windows `docs/`. |
| `docs/` | [Content and deployment notes](docs/CONTENT.md). |

## CI/CD

| Workflow | When | What |
| --- | --- | --- |
| [`ci`](.github/workflows/ci.yml) | push to `main`, pull requests | HTML validation (html-validate), link check of the site and Markdown, gitleaks. |
| [`deploy`](.github/workflows/deploy.yml) | push to `main` | Runs `ci`, then publishes `site/` to GitHub Pages. One-time setup: *Settings → Pages → Source: GitHub Actions*. |

## Related repositories

[alondra1-windows](https://github.com/nikita4sea/alondra1-windows) (the app) · [alondra1-backend](https://github.com/nikita4sea/alondra1-backend) · [alondra1-android](https://github.com/nikita4sea/alondra1-android) · [alondra1-iphone](https://github.com/nikita4sea/alondra1-iphone) · [alondra1-mac](https://github.com/nikita4sea/alondra1-mac)

## License

[MIT](LICENSE)
