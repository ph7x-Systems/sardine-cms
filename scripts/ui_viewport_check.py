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
DESKTOP_WIDTH = 1280
STICKY = ".admin-sticky-panel"


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
    sticky_checked = 0
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

            # A second pass at desktop width: the design system promises
            # the editor's preview follows the form instead of scrolling
            # away (ADR-0055). That promise is one CSS rule deep and the
            # theme's own layout can silently take it back, so it is
            # asserted by scrolling, not by reading the stylesheet.
            wide = browser.new_page(viewport={"width": DESKTOP_WIDTH, "height": HEIGHT})
            for path in paths:
                wide.goto(f"http://127.0.0.1:{port}{path}", wait_until="load")
                if not wide.locator(STICKY).count():
                    continue
                # Scroll with the wheel rather than window.scrollTo: the
                # theme can make a region the scroll container instead of
                # the page, and then scripted window scrolling is a
                # no-op — which would let the check pass on a panel that
                # never moves because nothing moves.
                #
                # The target is the end of the panel's own row, not the
                # end of the page: a sticky panel is released when its
                # column ends, and below the editor's side-by-side row
                # there is nothing for a preview to sit beside.
                need = wide.evaluate(
                    "(selector) => { const row = document.querySelector(selector)"
                    "   .closest('.row');"
                    " return Math.max(0, Math.round("
                    "   row.getBoundingClientRect().bottom - window.innerHeight)); }",
                    STICKY,
                )
                wide.mouse.move(DESKTOP_WIDTH // 2, HEIGHT // 2)
                for _ in range(need // 300):
                    wide.mouse.wheel(0, 300)
                if need % 300:
                    wide.mouse.wheel(0, need % 300)
                wide.wait_for_timeout(150)
                # Pinned means the panel's top stays inside the viewport
                # after scrolling to the end. "Still partly visible"
                # would pass for a panel that merely happens to sit near
                # the bottom of a short page.
                top = wide.evaluate(
                    "(selector) =>"
                    " Math.round(document.querySelector(selector).getBoundingClientRect().top)",
                    STICKY,
                )
                sticky_checked += 1
                if top < 0:
                    failures.append(
                        f"{path}: the preview scrolled {-top}px past the top of the "
                        f"viewport at {DESKTOP_WIDTH}px instead of staying put"
                    )
            wide.close()
            browser.close()
    finally:
        server.shutdown()
    if failures:
        for failure in failures:
            print(failure)
        print(f"FAIL: {len(failures)} screen(s) failed the viewport checks")
        return 1
    print(
        f"OK: no horizontal page scroll at {WIDTH}px across {checked} screens; "
        f"the preview stays in view on {sticky_checked} of them at {DESKTOP_WIDTH}px"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
