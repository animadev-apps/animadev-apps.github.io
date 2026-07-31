# AnimaDev website

General public website for **AnimaDev**, an independent application developer. The repository is organised so that each application can have its own information page and separate privacy documentation while sharing the site-wide design.

The planned public home page is:

<https://animadev-apps.github.io/>

The site uses plain HTML and one shared CSS file. It has no frameworks, build tools, external dependencies, cookies, analytics, advertisements, forms, or tracking scripts.

## Multi-application structure

```text
.
├── index.html                                      # General AnimaDev home
├── assets/styles.css                               # Shared responsive styles
├── apps/
│   └── calcolo-prezzi/
│       ├── index.html                              # Calcolo Prezzi app page
│       └── privacy/
│           ├── index.html                          # Manual language selection
│           ├── it/index.html                       # Italian Privacy Policy
│           ├── en/index.html                       # English Privacy Policy
│           ├── de/index.html                       # German Privacy Policy
│           ├── es/index.html                       # Spanish Privacy Policy
│           └── fr/index.html                       # French Privacy Policy
├── scripts/validate_site.py                        # Standard-library validator
└── .nojekyll                                       # Disable Jekyll processing
```

Future applications can be added under `apps/STABLE-NAME/`, each with an app page and, when needed, its own `privacy/` subtree. Stable lowercase slugs should be used so that one app’s documents never overlap with another app’s URLs.

## Calcolo Prezzi URLs

- App page: <https://animadev-apps.github.io/apps/calcolo-prezzi/>
- Privacy language selection: <https://animadev-apps.github.io/apps/calcolo-prezzi/privacy/>
- Italian: <https://animadev-apps.github.io/apps/calcolo-prezzi/privacy/it/>
- English: <https://animadev-apps.github.io/apps/calcolo-prezzi/privacy/en/>
- German: <https://animadev-apps.github.io/apps/calcolo-prezzi/privacy/de/>
- Spanish: <https://animadev-apps.github.io/apps/calcolo-prezzi/privacy/es/>
- French: <https://animadev-apps.github.io/apps/calcolo-prezzi/privacy/fr/>

The English policy is the recommended international fallback. Visitors always choose their language manually; there is no browser-language redirect.

## Local preview

From the repository root, run:

```sh
python3 -m http.server 8000
```

Then open <http://localhost:8000/>. Stop the server with `Ctrl+C`.

## Validation

The validator uses only the Python standard library:

```sh
python3 scripts/validate_site.py
```

It checks the application-scoped structure, document markup and metadata, accessibility basics, policy consistency, language navigation, relative links, forbidden legacy paths, trackers and remote assets, placeholder text, obvious secrets, and repository privacy hazards.

## Future GitHub Pages publication

GitHub Pages is not enabled by this repository. After the work has been reviewed and merged into `main`, a repository administrator can open **Settings → Pages**, choose **Deploy from a branch**, select the `main` branch and the repository root, then save. The expected public URL is <https://animadev-apps.github.io/>.

Publishing should happen only after the app’s Analytics implementation and this draft Privacy Policy have been checked and updated for the definitive release.
