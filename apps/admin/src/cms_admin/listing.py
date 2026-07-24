"""List-screen pagination (DS-19): a collection larger than the page
size never renders in full. One page size for every admin list."""

from collections.abc import Sequence

PAGE_SIZE = 25


def paginate[T](items: Sequence[T], page: int) -> tuple[list[T], dict[str, int]]:
    """One page of ``items`` plus the numbers the summary line and the
    pagination control need. ``page`` is clamped, never an error."""
    total = len(items)
    pages = max(1, -(-total // PAGE_SIZE))
    current = min(max(1, page), pages)
    first = (current - 1) * PAGE_SIZE
    shown = list(items[first : first + PAGE_SIZE])
    return shown, {
        "page": current,
        "pages": pages,
        "total": total,
        "first": first + 1 if shown else 0,
        "last": first + len(shown),
    }
