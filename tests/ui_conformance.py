"""The UI conformance suite (#244, ADR-0055): the panel's own rules,
executable.

Scope is deliberately narrow. Only rules that are **structurally
deterministic** from rendered HTML live here — a check that would need
a heuristic to guess intent stays a documented audit
(docs/UI_CONFORMANCE.md says which, and why). A small credible suite
beats a total one built on guesses.

Each check takes a parsed :class:`Rendered` page and raises
``AssertionError`` naming the rule it enforces.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from html.parser import HTMLParser

UI_CONFORMANCE_VERSION = 1

_VOID = {"input", "img", "br", "hr", "meta", "link"}
_CONTROLS = {"input", "select", "textarea"}


@dataclass
class _Block:
    """One region the checks care about, with its position in the
    document and what it contains."""

    kind: str
    start: int
    has_action: bool = False


@dataclass
class Rendered:
    """What the checks read: positions and counts, never styling."""

    path: str
    h1_texts: list[str] = field(default_factory=list)
    h1_badge_inside: bool = False
    breadcrumbs: int = 0
    open_details: int = 0
    visible_controls: int = 0
    """Controls a user can reach without opening a disclosure — the
    only count DS-8 compares across language fixtures."""
    body_rows: int = 0
    """Rows in the largest table body on the page."""
    paginations: int = 0
    filter_bars: list[int] = field(default_factory=list)
    summary_lines: list[int] = field(default_factory=list)
    tables: list[int] = field(default_factory=list)
    empty_states: list[_Block] = field(default_factory=list)


class _Parser(HTMLParser):
    def __init__(self, path: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page = Rendered(path=path)
        self._stack: list[tuple[str, list[str]]] = []
        self._closed_details = 0
        self._in_h1 = False
        self._empty_state_depth: int | None = None
        self._tbody_depth: int | None = None
        self._rows = 0
        self._position = 0

    # -- helpers ------------------------------------------------------
    def _classes(self, attrs: dict[str, str | None]) -> list[str]:
        return (attrs.get("class") or "").split()

    # -- parsing ------------------------------------------------------
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = self._classes(values)
        self._position += 1
        page = self.page

        if tag == "h1":
            self._in_h1 = True
            page.h1_texts.append("")
        elif tag == "details":
            if "open" in values:
                page.open_details += 1
            else:
                self._closed_details += 1
                self._stack.append(("details:closed", classes))
                return
        elif tag == "table":
            page.tables.append(self._position)
        elif tag == "tbody":
            self._tbody_depth = len(self._stack)
            self._rows = 0
        elif tag == "tr" and self._tbody_depth is not None:
            self._rows += 1
        elif tag in _CONTROLS:
            hidden = values.get("type") == "hidden"
            if not hidden and self._closed_details == 0:
                page.visible_controls += 1
        elif self._in_h1 and "badge" in classes:
            page.h1_badge_inside = True

        if "breadcrumb" in classes or "admin-breadcrumb" in classes:
            page.breadcrumbs += 1
        if "admin-filter-bar" in classes:
            page.filter_bars.append(self._position)
        if "admin-summary-line" in classes:
            page.summary_lines.append(self._position)
        if "pagination" in classes:
            page.paginations += 1
        if "admin-empty-state" in classes:
            page.empty_states.append(_Block("empty-state", self._position))
            self._empty_state_depth = len(self._stack)
        if self._empty_state_depth is not None and tag in ("a", "button"):
            page.empty_states[-1].has_action = True

        if tag not in _VOID:
            self._stack.append((tag, classes))

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1":
            self._in_h1 = False
        if not self._stack:
            return
        name, _classes = self._stack[-1]
        if tag == "details" and name == "details:closed":
            self._closed_details -= 1
            self._stack.pop()
            return
        if name == tag:
            self._stack.pop()
        if tag == "tbody":
            self.page.body_rows = max(self.page.body_rows, self._rows)
            self._tbody_depth = None
        if self._empty_state_depth is not None and len(self._stack) <= self._empty_state_depth:
            self._empty_state_depth = None

    def handle_data(self, data: str) -> None:
        if self._in_h1 and self.page.h1_texts:
            self.page.h1_texts[-1] += data


def parse(path: str, html: str) -> Rendered:
    parser = _Parser(path)
    parser.feed(html)
    return parser.page


# -- the checks -------------------------------------------------------

STANDALONE = ("/login", "/reset", "/setup", "/2fa")
"""Flows outside the shell — DS-2's declared exceptions."""


def check_one_h1_carrying_only_the_title(page: Rendered) -> None:
    """DS-1: exactly one ``h1``, and it holds the title alone — status
    badges render beside it, never inside."""
    assert len(page.h1_texts) == 1, f"{page.path}: {len(page.h1_texts)} h1 elements"
    assert not page.h1_badge_inside, f"{page.path}: a badge renders inside the h1"


def check_breadcrumbs(page: Rendered) -> None:
    """DS-2: every screen inside the shell carries breadcrumbs."""
    if page.path.startswith(STANDALONE):
        return
    assert page.breadcrumbs >= 1, f"{page.path}: no breadcrumb navigation"


def check_empty_states_offer_the_next_action(page: Rendered) -> None:
    """DS-7: an empty state states the meaning *and* offers the action."""
    for block in page.empty_states:
        assert block.has_action, f"{page.path}: an empty state carries no action"


def check_at_most_one_open_disclosure(page: Rendered) -> None:
    """DS-17: forms scale by depth — at most one section open at load."""
    assert page.open_details <= 1, f"{page.path}: {page.open_details} disclosures open at load"


def check_datatable_order(page: Rendered) -> None:
    """The DataTable contract (#250): filters → summary line → table.
    Only screens that have the parts are held to the order."""
    if not page.summary_lines or not page.tables:
        return
    summary = page.summary_lines[0]
    following = [position for position in page.tables if position > summary]
    assert following, f"{page.path}: a summary line with no table after it"
    table = following[0]
    bars = [position for position in page.filter_bars if position < table]
    if bars:
        assert bars[-1] < summary, f"{page.path}: the filter bar renders after the summary line"


def check_pagination_bounds_large_collections(page: Rendered, page_size: int) -> None:
    """DS-19: a collection larger than the page size never renders in
    full — one page plus a pagination control."""
    assert page.body_rows <= page_size, f"{page.path}: {page.body_rows} rows rendered at once"
    if page.body_rows == page_size:
        assert page.paginations >= 1, f"{page.path}: a full page without pagination"


def conformance_checks() -> tuple[tuple[str, Callable[[Rendered], None]], ...]:
    """The per-screen checks, in a stable order, for parametrized tests.
    Fixture-dependent checks (DS-19's large collection, DS-8's language
    scale) take extra arguments and run in their own tests."""
    return (
        ("one-h1-carrying-only-the-title", check_one_h1_carrying_only_the_title),
        ("breadcrumbs", check_breadcrumbs),
        ("empty-states-offer-the-next-action", check_empty_states_offer_the_next_action),
        ("at-most-one-open-disclosure", check_at_most_one_open_disclosure),
        ("datatable-order", check_datatable_order),
    )
