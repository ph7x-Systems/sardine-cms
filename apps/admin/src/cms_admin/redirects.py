"""Automatic redirects when a published entry's address changes.

Renaming a slug on published content breaks every existing link; the
panel records the old address in the project's redirect map instead
(the builder emits fallback pages and target configs from it). Chains
flatten (anything pointing at the old address points at the new one),
self-redirects never survive, and an address that becomes live again
drops its stale redirect — the live page wins.
"""

import logging
from pathlib import Path

from cms_build import urls
from cms_core import Article, ContentStatus, Page
from fastapi import Request

from cms_admin.publishing import _project

logger = logging.getLogger("cms_admin.redirects")


def merge_redirects(existing: dict[str, str], changes: dict[str, str]) -> dict[str, str]:
    """Fold address changes into the redirect map, flattened and safe."""
    merged = dict(existing)
    for old, new in changes.items():
        for source, destination in list(merged.items()):
            if destination == old:
                merged[source] = new  # flatten: A→old, old→new becomes A→new
        merged[old] = new
    live = set(changes.values())
    return {
        source: destination
        for source, destination in merged.items()
        if source != destination and source not in live
    }


def _entry_paths(project: object, entry: Article | Page) -> dict[str, str]:
    config = project.site  # type: ignore[attr-defined]
    paths: dict[str, str] = {}
    languages = [config.source_language, *config.languages]
    for language in languages:
        if isinstance(entry, Article):
            if language != config.source_language and language not in entry.translations:
                continue
            paths[language.value] = urls.article_path(config, entry, language)
        else:
            if language != config.source_language and language not in entry.translations:
                continue
            paths[language.value] = urls.page_path(entry, language, source=config.source_language)
    return paths


def _write_redirects(project_file: Path, redirects: dict[str, str]) -> None:
    """Rewrite the ``[redirects]`` table; the rest of the file is
    left exactly as the owner wrote it."""
    text = project_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    kept: list[str] = []
    in_table = False
    for line in lines:
        stripped = line.strip()
        if stripped == "[redirects]":
            in_table = True
            continue
        if in_table and stripped.startswith("["):
            in_table = False
        if not in_table:
            kept.append(line)
    while kept and not kept[-1].strip():
        kept.pop()
    if redirects:
        kept.extend(["", "[redirects]"])
        kept.extend(
            f'"{source}" = "{destination}"' for source, destination in sorted(redirects.items())
        )
    project_file.write_text("\n".join(kept) + "\n", encoding="utf-8")


async def record_slug_redirects(
    request: Request, before: Article | Page, after: Article | Page
) -> None:
    """Compare a published entry's addresses before and after a save and
    persist any change as a redirect. Never blocks the save."""
    try:
        if before.status is not ContentStatus.PUBLISHED:
            return
        project = _project(request)
        if project is None:
            return
        old_paths = _entry_paths(project, before)
        new_paths = _entry_paths(project, after)
        changes = {
            old: new_paths[code]
            for code, old in old_paths.items()
            if code in new_paths and (new := new_paths[code]) != old
        }
        if not changes:
            return
        merged = merge_redirects(dict(project.site.redirects), changes)
        _write_redirects(project.directory / "sardine.toml", merged)
        from cms_admin.audit import record as audit_record

        for old, new in sorted(changes.items()):
            await audit_record(request, "system", "redirected", "url", old, new)
    except Exception:  # pragma: no cover - never break the editorial save
        logger.exception("recording slug redirects failed")
