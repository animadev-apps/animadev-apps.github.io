#!/usr/bin/env python3
"""Validate the AnimaDev static site using only the Python standard library."""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parent.parent
EMAIL = "animadev.apps@gmail.com"
DATE = "2026-07-31"
APP_PAGE = Path("apps/calcolo-prezzi/index.html")
PRIVACY_INDEX = Path("apps/calcolo-prezzi/privacy/index.html")
POLICY_ROOT = Path("apps/calcolo-prezzi/privacy")

HTML_LANGS = {
    Path("index.html"): "it",
    APP_PAGE: "it",
    PRIVACY_INDEX: "it",
    POLICY_ROOT / "it/index.html": "it",
    POLICY_ROOT / "en/index.html": "en",
    POLICY_ROOT / "de/index.html": "de",
    POLICY_ROOT / "es/index.html": "es",
    POLICY_ROOT / "fr/index.html": "fr",
}

REQUIRED_FILES = [
    *HTML_LANGS,
    Path("assets/styles.css"),
    Path("scripts/validate_site.py"),
    Path("README.md"),
    Path(".nojekyll"),
]

POLICIES = {
    POLICY_ROOT / "it/index.html": "Calcolo Prezzi",
    POLICY_ROOT / "en/index.html": "Price Calculator",
    POLICY_ROOT / "de/index.html": "Preisrechner",
    POLICY_ROOT / "es/index.html": "Calculadora de precios",
    POLICY_ROOT / "fr/index.html": "Calculateur de prix",
}

EVENT_KEYS = ("calculator_opened", "calculate_pressed", "calculation_completed")
APP_TARGET = "/apps/calcolo-prezzi/"
PRIVACY_TARGET = "/apps/calcolo-prezzi/privacy/"
LANG_TARGETS = tuple(f"{PRIVACY_TARGET}{language}/" for language in ("it", "en", "de", "es", "fr"))
NEW_PUBLIC_URLS = (
    "https://animadev-apps.github.io/",
    "https://animadev-apps.github.io/apps/calcolo-prezzi/",
    "https://animadev-apps.github.io/apps/calcolo-prezzi/privacy/",
    *(f"https://animadev-apps.github.io/apps/calcolo-prezzi/privacy/{language}/" for language in ("it", "en", "de", "es", "fr")),
)
ESSENTIAL_SECTION_NUMBERS = tuple(f"{number}." for number in range(1, 18))


class SiteHTMLParser(HTMLParser):
    """Collect structural facts while relying on HTMLParser for markup."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.start_tags: list[tuple[str, dict[str, str]]] = []
        self.links: list[dict[str, str]] = []
        self.scripts: list[dict[str, str]] = []
        self.stylesheets: list[dict[str, str]] = []
        self.h1_count = 0
        self.title_depth = 0
        self.title_text: list[str] = []
        self.descriptions: list[str] = []
        self.charsets: list[str] = []
        self.viewports: list[str] = []
        self.html_lang: str | None = None
        self.time_datetimes: list[str] = []
        self.heading_levels: list[int] = []
        self.policy_section_depth = 0
        self.policy_section_h2_depth = 0
        self.policy_headings: list[str] = []
        self.current_policy_heading: list[str] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {key: value or "" for key, value in attrs_list}
        self.start_tags.append((tag, attrs))
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "html":
            self.html_lang = attrs.get("lang")
        elif tag == "h1":
            self.h1_count += 1
            self.heading_levels.append(1)
        elif tag in ("h2", "h3", "h4", "h5", "h6"):
            self.heading_levels.append(int(tag[1]))
        elif tag == "title":
            self.title_depth += 1
        elif tag == "meta":
            if "charset" in attrs:
                self.charsets.append(attrs["charset"].lower())
            if attrs.get("name", "").lower() == "description":
                self.descriptions.append(attrs.get("content", "").strip())
            if attrs.get("name", "").lower() == "viewport":
                self.viewports.append(attrs.get("content", "").strip())
        elif tag == "a":
            self.links.append(attrs)
        elif tag == "script":
            self.scripts.append(attrs)
        elif tag == "link" and "stylesheet" in attrs.get("rel", "").lower().split():
            self.stylesheets.append(attrs)
        elif tag == "time":
            self.time_datetimes.append(attrs.get("datetime", ""))

        classes = set(attrs.get("class", "").split())
        if tag == "section" and "policy-section" in classes:
            self.policy_section_depth += 1
        elif tag == "h2" and self.policy_section_depth:
            self.policy_section_h2_depth += 1
            self.current_policy_heading = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self.title_depth:
            self.title_depth -= 1
        elif tag == "h2" and self.policy_section_h2_depth:
            heading = "".join(self.current_policy_heading).strip()
            self.policy_headings.append(heading)
            self.policy_section_h2_depth -= 1
            self.current_policy_heading = []
        elif tag == "section" and self.policy_section_depth:
            self.policy_section_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.title_depth:
            self.title_text.append(data)
        if self.policy_section_h2_depth:
            self.current_policy_heading.append(data)


def report(errors: list[str], path: Path | str, message: str) -> None:
    errors.append(f"{path}: {message}")


def local_target(page: Path, href: str) -> Path | None:
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc or href.startswith(("mailto:", "tel:", "#")):
        return None
    raw_path = unquote(parsed.path)
    if not raw_path:
        return None
    candidate = (ROOT / page.parent / raw_path).resolve()
    try:
        candidate.relative_to(ROOT)
    except ValueError:
        return candidate
    if raw_path.endswith("/") or candidate.is_dir():
        candidate = candidate / "index.html"
    return candidate


def canonical_site_path(target: Path) -> str:
    try:
        relative = target.resolve().relative_to(ROOT)
    except ValueError:
        return ""
    value = "/" + relative.as_posix()
    return value.removesuffix("index.html")


def link_targets(page: Path, parser: SiteHTMLParser) -> set[str]:
    """Return canonical paths for local links in one parsed page."""
    return {
        canonical_site_path(target)
        for attrs in parser.links
        if (target := local_target(page, attrs.get("href", ""))) is not None
    }


def validate_html(page: Path, expected_lang: str, errors: list[str]) -> SiteHTMLParser | None:
    full_path = ROOT / page
    if not full_path.is_file():
        return None
    raw = full_path.read_text(encoding="utf-8")
    if not raw.strip():
        report(errors, page, "page is empty")
        return None

    parser = SiteHTMLParser()
    try:
        parser.feed(raw)
        parser.close()
    except Exception as exc:  # HTMLParser errors should be clear to maintainers.
        report(errors, page, f"HTML parsing failed: {exc}")
        return None

    lowered = raw.lower()
    if not re.match(r"\s*<!doctype\s+html\s*>", raw, flags=re.IGNORECASE):
        report(errors, page, "missing HTML doctype")
    for tag in ("html", "head", "body"):
        if not any(found_tag == tag for found_tag, _ in parser.start_tags):
            report(errors, page, f"missing <{tag}> element")
    if "utf-8" not in parser.charsets:
        report(errors, page, "missing <meta charset=\"utf-8\">")
    if parser.html_lang != expected_lang:
        report(errors, page, f"expected lang={expected_lang!r}, found {parser.html_lang!r}")
    if parser.h1_count != 1:
        report(errors, page, f"expected exactly one h1, found {parser.h1_count}")
    if not "".join(parser.title_text).strip():
        report(errors, page, "missing or empty title")
    if not parser.descriptions or any(not value for value in parser.descriptions):
        report(errors, page, "missing or empty meta description")
    if not parser.viewports or "width=device-width" not in parser.viewports[0]:
        report(errors, page, "missing responsive viewport metadata")
    for previous, current in zip(parser.heading_levels, parser.heading_levels[1:]):
        if current > previous + 1:
            report(errors, page, f"heading level jumps from h{previous} to h{current}")
    if EMAIL not in raw:
        report(errors, page, "missing contact email")
    if "AnimaDev" not in raw:
        report(errors, page, "missing developer name AnimaDev")
    if page in (Path("index.html"), APP_PAGE, PRIVACY_INDEX) and "Calcolo Prezzi" not in raw:
        report(errors, page, "missing app name Calcolo Prezzi")

    if parser.scripts:
        report(errors, page, "script elements are not allowed on this static site")
    for attrs in parser.stylesheets:
        href = attrs.get("href", "")
        if href.startswith(("http://", "https://", "//")):
            report(errors, page, f"remote stylesheet is forbidden: {href}")
        target = local_target(page, href)
        if target is None or not target.is_file():
            report(errors, page, f"broken local stylesheet: {href}")
        elif canonical_site_path(target) != "/assets/styles.css":
            report(errors, page, f"page must use the shared /assets/styles.css file: {href}")
    if len(parser.stylesheets) != 1:
        report(errors, page, f"expected exactly one local stylesheet, found {len(parser.stylesheets)}")

    for tag, attrs in parser.start_tags:
        if tag == "form":
            report(errors, page, "forms are not allowed")
        if tag in ("img", "iframe", "audio", "video", "source"):
            source = attrs.get("src", "")
            if source.startswith(("http://", "https://", "//")):
                report(errors, page, f"remote media resource is forbidden: {source}")

    tracker_code = (
        "gtag(", "googletagmanager.com", "google-analytics.com", "fbq(",
        "connect.facebook.net", "adsbygoogle", "doubleclick.net",
        "localstorage", "serviceworker", "navigator.serviceworker", "fingerprintjs",
    )
    for marker in tracker_code:
        if marker in lowered:
            report(errors, page, f"tracker implementation marker found: {marker}")
    for tag, attrs in parser.start_tags:
        tokens = set((attrs.get("id", "") + " " + attrs.get("class", "")).lower().replace("_", "-").split())
        if {"cookie-banner", "cookie-consent", "consent-banner"} & tokens:
            report(errors, page, f"cookie banner marker found on <{tag}>")

    for attrs in parser.links:
        href = attrs.get("href", "")
        if not href:
            report(errors, page, "link without href")
            continue
        parsed = urlsplit(href)
        if parsed.scheme in ("http", "https"):
            if href.startswith("https://animadev-apps.github.io/privacy"):
                report(errors, page, f"legacy public Privacy Policy URL found: {href}")
            rel = set(attrs.get("rel", "").split())
            if attrs.get("target") != "_blank":
                report(errors, page, f"external link must use target=_blank: {href}")
            if not {"noopener", "noreferrer"}.issubset(rel):
                report(errors, page, f"external link missing rel=noopener noreferrer: {href}")
            continue
        target = local_target(page, href)
        if target is not None and not target.is_file():
            report(errors, page, f"broken relative link: {href}")
        if target is not None and canonical_site_path(target).startswith("/privacy/"):
            report(errors, page, f"legacy internal Privacy Policy link found: {href}")
        if parsed.fragment and not parsed.path and parsed.fragment not in parser.ids:
            report(errors, page, f"missing local fragment target: #{parsed.fragment}")

    if not any("skip-link" in attrs.get("class", "").split() for attrs in parser.links):
        report(errors, page, "missing skip link")
    if not any(attrs.get("href") == f"mailto:{EMAIL}" for attrs in parser.links):
        report(errors, page, "contact email is not a mailto link")
    if DATE not in parser.time_datetimes:
        report(errors, page, f"missing date in a time element with datetime={DATE}")

    placeholders = ("lorem ipsum", "todo:", "tbd", "coming soon", "placeholder", "{{", "}}", "your app", "your email")
    for marker in placeholders:
        if marker in lowered:
            report(errors, page, f"placeholder or untranslated template marker found: {marker}")
    return parser


def validate_policy(page: Path, app_name: str, parser: SiteHTMLParser, errors: list[str]) -> None:
    raw = (ROOT / page).read_text(encoding="utf-8")
    if app_name not in raw:
        report(errors, page, f"missing localised app name {app_name!r}")
    if DATE not in parser.time_datetimes:
        report(errors, page, f"missing date in a time element with datetime={DATE}")
    if parser.time_datetimes.count(DATE) < 2:
        report(errors, page, "effective and updated dates are both required")
    for key in (*EVENT_KEYS, "calculator_id"):
        if key not in raw:
            report(errors, page, f"missing Analytics key {key}")

    targets = link_targets(page, parser)
    for expected in LANG_TARGETS:
        if expected not in targets:
            report(errors, page, f"missing language link to {expected}")
    for expected in ("/", APP_TARGET, PRIVACY_TARGET):
        if expected not in targets:
            report(errors, page, f"missing navigation link to {expected}")
    if not any(attrs.get("aria-current") == "page" and attrs.get("lang") == HTML_LANGS[page] for attrs in parser.links):
        report(errors, page, "active language link is missing aria-current=page")

    headings = parser.policy_headings
    if len(headings) != len(ESSENTIAL_SECTION_NUMBERS):
        report(errors, page, f"expected 17 essential policy sections, found {len(headings)}")
    else:
        for expected, heading in zip(ESSENTIAL_SECTION_NUMBERS, headings):
            if not heading.startswith(expected):
                report(errors, page, f"section order mismatch: expected heading {expected}, found {heading!r}")


def validate_language_quality(errors: list[str]) -> None:
    italian_markers = (
        "questa policy riguarda", "dati memorizzati localmente", "ultimo aggiornamento:",
        "torna alla pagina", "non vengono inviati", "finalità del trattamento",
    )
    for language in ("de", "es", "fr"):
        page = POLICY_ROOT / f"{language}/index.html"
        lowered = (ROOT / page).read_text(encoding="utf-8").lower()
        for marker in italian_markers:
            if marker in lowered:
                report(errors, page, f"obvious Italian text found: {marker!r}")

    french_page = POLICY_ROOT / "fr/index.html"
    french = (ROOT / french_page).read_text(encoding="utf-8").lower()
    for marker in ("datenschutzerklärung", "speicherdauer", "zur startseite", "nutzerkonto"):
        if marker in french:
            report(errors, french_page, f"obvious German text found: {marker!r}")

    non_english = ("it", "de", "es", "fr")
    for language in non_english:
        page = POLICY_ROOT / f"{language}/index.html"
        lowered = (ROOT / page).read_text(encoding="utf-8").lower()
        for marker in ("effective date:", "last updated:", "back to top", "data controller:", "privacy policy template"):
            if marker in lowered:
                report(errors, page, f"obvious English template text found: {marker!r}")


def validate_repository_safety(errors: list[str]) -> None:
    forbidden_names = {
        "google-services.json", ".env", ".env.local", ".env.production",
        "credentials.json", "service-worker.js", "sw.js",
    }
    text_suffixes = {".html", ".css", ".py", ".md", ".txt", ".json", ".yml", ".yaml"}
    secret_patterns = {
        "GitHub token": re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
        "Google/Firebase API key": re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
        "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        "assigned password": re.compile(r"(?i)\bpassword\s*[:=]\s*[\"'][^\"']{6,}[\"']"),
    }
    privacy_hazards = {
        "old personal email": re.compile(r"frantumatore-vulcanico" + r"@live" + r"\.it", re.IGNORECASE),
        "Italian phone number": re.compile(r"(?<!\w)(?:\+39|0039)[\s.-]*(?:\d[\s.-]*){8,12}(?!\w)"),
        "home-address label": re.compile(r"(?i)\b(?:home address|indirizzo di casa|wohnanschrift|domicilio particular|adresse personnelle)\b"),
    }

    for path in ROOT.rglob("*"):
        if ".git" in path.parts or not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if path.stat().st_size == 0:
            report(errors, relative, "file is empty")
        if path.name in forbidden_names or path.name.startswith(".env."):
            report(errors, relative, "forbidden credential/configuration file present")
        # This validator contains the hazard signatures as source code; scanning
        # itself would report those definitions instead of repository data.
        if relative == Path("scripts/validate_site.py"):
            continue
        if path.suffix.lower() not in text_suffixes and path.name != ".nojekyll":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for label, pattern in {**secret_patterns, **privacy_hazards}.items():
            if pattern.search(text):
                report(errors, relative, f"possible {label} found")


def require_navigation(
    page: Path,
    parser: SiteHTMLParser | None,
    expected_targets: tuple[str, ...],
    errors: list[str],
) -> None:
    if parser is None:
        return
    targets = link_targets(page, parser)
    for expected in expected_targets:
        if expected not in targets:
            report(errors, page, f"missing required navigation link to {expected}")


def validate_app_structure(parsers: dict[Path, SiteHTMLParser], errors: list[str]) -> None:
    """Validate app-scoped routes, legacy removal, and navigation."""
    old_root = ROOT / "privacy"
    if old_root.exists():
        report(errors, Path("privacy"), "legacy Privacy Policy directory must not exist")

    discovered = {
        path.relative_to(ROOT)
        for path in ROOT.glob("**/privacy/*/index.html")
        if path.is_file()
    }
    expected = set(POLICIES)
    for extra in sorted(discovered - expected):
        report(errors, extra, "unexpected or duplicate Privacy Policy page")
    for missing in sorted(expected - discovered):
        report(errors, missing, "expected Privacy Policy page was not discovered")

    require_navigation(
        Path("index.html"), parsers.get(Path("index.html")),
        (APP_TARGET, PRIVACY_TARGET, *LANG_TARGETS), errors,
    )
    require_navigation(
        APP_PAGE, parsers.get(APP_PAGE),
        ("/", PRIVACY_TARGET, *LANG_TARGETS), errors,
    )
    require_navigation(
        PRIVACY_INDEX, parsers.get(PRIVACY_INDEX),
        ("/", APP_TARGET, *LANG_TARGETS), errors,
    )


def validate_readme(errors: list[str]) -> None:
    readme_path = ROOT / "README.md"
    if not readme_path.is_file():
        return
    text = readme_path.read_text(encoding="utf-8")
    for url in NEW_PUBLIC_URLS:
        if url not in text:
            report(errors, Path("README.md"), f"missing new public URL: {url}")
    if "https://animadev-apps.github.io/privacy" in text:
        report(errors, Path("README.md"), "legacy /privacy/ public URL found")
    if "apps/STABLE-NAME/" not in text:
        report(errors, Path("README.md"), "missing future multi-application structure guidance")


def main() -> int:
    errors: list[str] = []
    for required in REQUIRED_FILES:
        if not (ROOT / required).is_file():
            report(errors, required, "required file is missing")

    parsers: dict[Path, SiteHTMLParser] = {}
    for page, lang in HTML_LANGS.items():
        parser = validate_html(page, lang, errors)
        if parser is not None:
            parsers[page] = parser

    for page, app_name in POLICIES.items():
        parser = parsers.get(page)
        if parser is not None:
            validate_policy(page, app_name, parser, errors)

    validate_app_structure(parsers, errors)
    validate_readme(errors)

    css_path = ROOT / "assets/styles.css"
    if css_path.is_file():
        css = css_path.read_text(encoding="utf-8")
        if re.search(r"@import\s+|url\(\s*[\"']?(?:https?:)?//", css, re.IGNORECASE):
            report(errors, Path("assets/styles.css"), "remote CSS import or asset found")
        for feature in ("prefers-color-scheme", "prefers-reduced-motion", "@media print", ":focus-visible"):
            if feature not in css:
                report(errors, Path("assets/styles.css"), f"missing required CSS feature {feature}")

    validate_language_quality(errors)
    validate_repository_safety(errors)

    if errors:
        print(f"Site validation failed with {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        "Site validation passed: "
        f"{len(HTML_LANGS)} HTML pages, one app route, and "
        f"{len(POLICIES)} complete policy translations checked."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
