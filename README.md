# ezuno Website

Static product website for [ezuno](https://www.ezuno.com/).

## About

The website contains 20 HTML pages with product information, pricing, support
and an installer download. Images and fonts are served locally; styling and
interactions are implemented in `assets/site.css` and `assets/site.js`.

The site runs without WordPress, PHP or a database. License requests, sales
enquiries and support buttons open email drafts addressed to `ezuno@ezuno.com`.
The product video loads Vimeo when the visitor starts playback.

## Build

```sh
python tools/build_site.py
python tools/verify_deployment.py --check-source
```

The build checks the bundled licenses and fonts, assembles the installer and
creates the complete website in `_site/`, replacing any previous build there.
Only website files are included in the output.
