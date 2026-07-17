"""Built-in minimal theme: semantic HTML, zero inline styles, local assets.

Projects can override any template or asset without forking: files under the
project's ``theme/templates`` and ``theme/assets`` directories take precedence
over the theme's own (ADR-0007).
"""

from pathlib import Path

from cms_build.themes.jinja import JinjaTheme


class DefaultTheme(JinjaTheme):
    name = "default"

    def __init__(self, overrides: Path | None = None) -> None:
        super().__init__(layers=("cms_build.themes.default",), overrides=overrides)
