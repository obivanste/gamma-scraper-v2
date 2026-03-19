# Gamma to PDF Scraper

> **⚠️ ARCHIVED — This is v2.**
>
> Development continues in **[gamma-to-pdf-live](https://github.com/obivanste/gamma-to-pdf-live)** — the final, actively maintained version.

Converts any public [Gamma.app](https://gamma.app) document into a clean, seamless PDF using a headless Chromium browser.

## Features

- Works on any public Gamma doc URL (pass as CLI argument)
- Bypasses Gamma's bot detection (headless fingerprint masking)
- Smart scroll — re-checks page height to catch all lazy-loaded content
- Permanently removes Gamma's UI chrome (topbar, nav) from the DOM before export
- Validates landing page to catch auth walls or redirects early
- Auto-derives output filename from the document URL slug
- Optional zoom control via environment variable
- Outputs a uniform, seamlessly paginated A4 PDF

---

## Quick Start

### 1. Install dependencies

```bash
pip install playwright
playwright install chromium
```

### 2. Run

```bash
# Default URL (hardcoded)
python3 gamma_to_pdf.py

# Any public Gamma doc
python3 gamma_to_pdf.py https://gamma.app/docs/your-doc-slug?mode=doc

# With zoom (e.g. 80%)
ZOOM=0.8 python3 gamma_to_pdf.py
```

Output PDF is saved to `exports/<document-title>.pdf`.

---

## How It Works

1. **Bot detection bypass** — launches Chromium with `--disable-blink-features=AutomationControlled`, sets a real macOS Chrome user agent, and removes the `navigator.webdriver` flag via an init script
2. **Page load** — navigates with `domcontentloaded` + 8s wait to allow Gamma's JS and any bot challenges to fully resolve
3. **Doc ID validation** — extracts the doc ID from the URL and confirms the landed page matches; saves `landed.png` on failure for debugging
4. **Smart scroll** — scrolls the full page height in steps, re-checking `scrollHeight` after each pass so newly revealed lazy-loaded cards are also triggered
5. **UI chrome removal** — permanently removes all `position: fixed` and `position: sticky` elements from the DOM (Gamma's topbar, nav buttons, etc.). Unlike CSS hiding, removed DOM nodes cannot be re-inserted by React
6. **PDF export** — uses Playwright's built-in `page.pdf()` to render a uniform A4 document with full background colours and minimal margins

---

## Project History

This is the third iteration of the Gamma scraper. Each version contributed techniques that were carried forward.

### v1 — `gamma_scraper_v1` (Node.js / Playwright)

**Language:** JavaScript (ES Modules)
**Approach:** Card-by-card screenshots merged into a PDF via `pdf-lib`

Key techniques introduced:
- CLI URL argument with `mode=doc` normalisation
- Doc ID extraction and landing page validation
- Smart scroll with `scrollHeight` re-check loop (handles lazy-loaded content)
- CSS class injection (`__scrape-hide`) to suppress `fixed`/`sticky` overlays
- Per-card overlay re-application to survive React re-renders
- Bounding box validation — skips cards smaller than 50×50px
- Capture summary with card count, width/height ranges, and outlier detection
- Auto-derived PDF filename from URL slug
- Organised `out/` (PNGs) and `exports/` (PDF) directories
- Optional `ZOOM` env var support

Known limitation: No bot detection bypass — hit Gamma's "Just a moment..." challenge wall on headless browsers.

---

### v2 initial — `gamma_scraper_new` → renamed `gamma_scraper_v2` (Python / Playwright)

**Language:** Python 3 async
**Approach:** Full-page `page.pdf()` export

Key techniques introduced:
- Bot detection bypass: `--disable-blink-features=AutomationControlled`, real Chrome user agent, `navigator.webdriver` removal via `add_init_script`
- 8-second post-load wait to allow bot challenge clearance
- Python async architecture with Playwright

Known limitations:
- Originally used `networkidle` wait which timed out (Gamma makes constant background requests). Fixed by switching to `domcontentloaded` + explicit timeout
- First working export was 103MB / 114 pages but included Gamma's topbar on every page — fixed elements were not removed before export

---

### v2 final — this repo

**Approach:** `page.pdf()` with full DOM removal of UI chrome

Combined the best of both prior versions:

| Feature | Source |
|---|---|
| Bot detection bypass | v2 initial |
| Python async + Playwright | v2 initial |
| CLI URL argument | v1 |
| `mode=doc` URL normalisation | v1 |
| Doc ID landing validation | v1 |
| Smart scroll with height re-check | v1 |
| Auto-derived PDF filename | v1 |
| `ZOOM` env var | v1 |
| Seamless `page.pdf()` export | v2 initial |
| DOM removal of fixed/sticky elements | New |

**Key improvement over both predecessors:** Instead of CSS-hiding the Gamma topbar (which React can override) or using a CSS class toggle (which React re-renders away), the final version calls `el.remove()` on all `position: fixed` and `position: sticky` elements after scrolling. Removed DOM nodes are gone for the lifetime of the page — React cannot reconcile them back in. This cleanly eliminates the topbar from every page of the exported PDF.

---

## File Structure

```
gamma_scraper_v2/
├── gamma_to_pdf.py   # Main script
├── requirements.txt  # Dependencies
├── README.md         # This file
└── exports/          # Output PDFs (git-ignored)
```

---

## Requirements

- Python 3.9+
- `playwright` (pip)
- Chromium (via `playwright install chromium`)
