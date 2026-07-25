"""DS-6 gate: no admin screen scrolls horizontally at 320 px.

The measurement matters. Comparing `scrollWidth` against the viewport
reports content that is correctly clipped inside an `overflow-x: auto`
container as if the page overflowed — that false positive sent one
audit chasing a bug that did not exist. The honest test is the user's:
try to scroll the document sideways and see whether it moves.

Wide content is still allowed to scroll *inside its own container* —
that is what the design system asks for; only the page must stay put.

Usage:
    python scripts/ui_viewport_check.py <admin_snapshot_dir> [paths...]
"""

import http.server
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

WIDTH = 320
HEIGHT = 900


def _serve(directory: Path) -> tuple[socketserver.TCPServer, int]:
    handler = lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(  # noqa: E731
        *args, directory=str(directory), **kwargs
    )
    server = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print("usage: ui_viewport_check.py <admin_snapshot_dir> [paths...]", file=sys.stderr)
        return 2
    site_dir = Path(args[0]).resolve()
    paths = args[1:]
    if not paths:
        print("no paths given", file=sys.stderr)
        return 2
    server, port = _serve(site_dir)
    failures: list[str] = []
    checked = 0
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
            for path in paths:
                page.goto(f"http://127.0.0.1:{port}{path}", wait_until="load")
                moved = page.evaluate(
                    "() => { window.scrollTo(99999, 0); const x = window.scrollX;"
                    " window.scrollTo(0, 0); return x; }"
                )
                checked += 1
                if moved > 0:
                    failures.append(f"{path}: the page scrolled {moved}px sideways at {WIDTH}px")
            page.close()
            browser.close()
    finally:
        server.shutdown()
    if failures:
        for failure in failures:
            print(failure)
        print(f"FAIL: {len(failures)} screen(s) scroll horizontally at {WIDTH}px")
        return 1
    print(f"OK: no horizontal page scroll at {WIDTH}px across {checked} screens")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
