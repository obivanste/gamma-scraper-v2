import asyncio
import sys
import re
import os
from pathlib import Path
from playwright.async_api import async_playwright

# ── URL handling ─────────────────────────────────────────────────────────────
DEFAULT_URL = "https://gamma.app/docs/Obzias-84-Page-Guide-on-Everything-You-Need-to-Know-to-Maximize-E-e6kg16jqhekko21?mode=doc"
RAW_URL = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL

# Force mode=doc for stable rendering
TARGET_URL = re.sub(r"([?&])mode=[^&]*", "", RAW_URL)
sep = "&" if "?" in TARGET_URL else "?"
TARGET_URL = f"{TARGET_URL}{sep}mode=doc"

# Extract doc ID for landing validation
_id_match = re.search(r"/docs/[^/?]+-([a-z0-9]{10,})", TARGET_URL, re.IGNORECASE)
EXPECTED_DOC_ID = _id_match.group(1) if _id_match else None

# Optional zoom: ZOOM=0.75 python gamma_to_pdf.py
ZOOM = float(os.environ.get("ZOOM", "1"))


# ── Helpers ──────────────────────────────────────────────────────────────────
async def smart_scroll(page):
    """Scroll with height re-check so all lazy-loaded content is triggered."""
    await page.evaluate("""async () => {
        const scroller = document.scrollingElement ?? document.documentElement;
        const step = Math.max(window.innerHeight, 600);
        let prev = -1;
        while (true) {
            const total = scroller.scrollHeight;
            if (total === prev) break;
            prev = total;
            for (let y = 0; y < total; y += step) {
                scroller.scrollTop = y;
                await new Promise(r => setTimeout(r, 180));
            }
            await new Promise(r => setTimeout(r, 600));
        }
        scroller.scrollTop = 0;
    }""")


async def remove_ui_chrome(page):
    """Permanently remove all fixed/sticky UI elements from the DOM.
    Unlike CSS hiding, removed nodes cannot be re-inserted by React."""
    removed = await page.evaluate("""() => {
        let count = 0;
        document.querySelectorAll('*').forEach(el => {
            const pos = window.getComputedStyle(el).position;
            if (pos === 'fixed' || pos === 'sticky') {
                el.remove();
                count++;
            }
        });
        return count;
    }""")
    return removed


# ── Main ─────────────────────────────────────────────────────────────────────
async def main():
    print(f"Target URL : {TARGET_URL}")
    if ZOOM != 1:
        print(f"Zoom       : {round(ZOOM * 100)}%")

    exports_dir = Path("exports")
    exports_dir.mkdir(exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        page = await context.new_page()
        page.set_default_timeout(120_000)
        page.set_default_navigation_timeout(120_000)

        print("Opening Gamma doc...")
        await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=120_000)
        await page.wait_for_timeout(8000)  # allow bot challenge to clear

        # Validate landing
        landed_url = page.url
        if EXPECTED_DOC_ID and EXPECTED_DOC_ID not in landed_url:
            await page.screenshot(path="landed.png", full_page=True)
            raise RuntimeError(f"Did not land on expected doc. URL={landed_url}")

        await page.wait_for_selector("[data-card-id]", timeout=30_000)
        await page.wait_for_timeout(1500)

        if ZOOM != 1:
            await page.evaluate(f"document.documentElement.style.zoom = '{ZOOM}'")
            await page.wait_for_timeout(500)

        print("Scrolling to load all content...")
        await smart_scroll(page)
        await page.wait_for_timeout(1000)

        print("Removing UI chrome...")
        removed = await remove_ui_chrome(page)
        print(f"  Removed {removed} fixed/sticky element(s).")
        await page.wait_for_timeout(500)

        # Derive output filename from URL slug
        slug_match = re.search(r"/docs/([^/?]+)", TARGET_URL)
        slug = slug_match.group(1) if slug_match else "gamma-export"
        title = re.sub(r"-[a-z0-9]{10,}$", "", slug, flags=re.IGNORECASE).replace("-", " ").strip() or "gamma-export"
        out_pdf = exports_dir / f"{title}.pdf"

        print("Exporting PDF...")
        await page.pdf(
            path=str(out_pdf),
            format="A4",
            print_background=True,
            margin={"top": "8mm", "right": "8mm", "bottom": "8mm", "left": "8mm"},
        )

        await browser.close()
        print(f"Done → {out_pdf}")


if __name__ == "__main__":
    asyncio.run(main())
