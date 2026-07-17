"""Shared Jinja theme base.

A theme is template layers plus asset layers. Later layers shadow earlier
ones, and the project's overrides directory (ADR-0007) always wins. The
built-in default theme and installable themes (e.g. the reference theme)
both build on this class instead of duplicating environment setup.
"""

from collections.abc import Mapping
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path

from jinja2 import (
    BaseLoader,
    ChoiceLoader,
    Environment,
    FileSystemLoader,
    PackageLoader,
    select_autoescape,
)


class JinjaTheme:
    """Compose a theme from ordered template/asset layers.

    ``layers`` are package names ordered most-specific first (each ships
    ``templates/`` and optionally ``assets/``). The overrides directory, when
    given, is prepended for templates; for assets, base layers load first and
    more specific layers — then overrides — replace earlier entries.
    """

    name = "jinja"

    def __init__(self, layers: tuple[str, ...], overrides: Path | None = None) -> None:
        self._layers = layers
        self._overrides = overrides
        loaders: list[BaseLoader] = []
        if overrides is not None and (overrides / "templates").is_dir():
            loaders.append(FileSystemLoader(overrides / "templates"))
        loaders.extend(PackageLoader(package, "templates") for package in layers)
        self._environment = Environment(
            loader=ChoiceLoader(loaders),
            autoescape=select_autoescape(default=True, default_for_string=True),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, kind: str, context: Mapping[str, object]) -> str:
        template = self._environment.get_template(f"{kind}.html.j2")
        return template.render(**context) + "\n"

    def assets(self) -> Mapping[str, bytes]:
        merged: dict[str, bytes] = {}
        for package in reversed(self._layers):
            merged.update(_package_assets(package))
        if self._overrides is not None and (self._overrides / "assets").is_dir():
            for path in sorted((self._overrides / "assets").rglob("*")):
                if path.is_file():
                    relative = path.relative_to(self._overrides / "assets").as_posix()
                    merged[f"assets/{relative}"] = path.read_bytes()
        return merged


def _package_assets(package: str) -> dict[str, bytes]:
    root = resources.files(package) / "assets"
    collected: dict[str, bytes] = {}
    if not root.is_dir():
        return collected

    def _walk(node: Traversable, prefix: str) -> None:
        for entry in sorted(node.iterdir(), key=lambda item: item.name):
            if entry.is_file():
                collected[f"{prefix}/{entry.name}"] = entry.read_bytes()
            elif entry.is_dir():
                _walk(entry, f"{prefix}/{entry.name}")

    _walk(root, "assets")
    return collected
