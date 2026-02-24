from pathlib import Path


def capture_chart_screenshot(url: str, output_path: str, wait_ms: int = 8000) -> str:
    """Capture TradingView chart screenshot using Playwright.
    Returns saved path. Raises on failure.
    """
    from playwright.sync_api import sync_playwright

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 900})
        page.set_default_timeout(90000)
        page.goto(url, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(wait_ms)
        # viewport screenshot is faster/more stable than full_page on heavy sites
        page.screenshot(path=str(out), full_page=False)
        browser.close()

    return str(out)
