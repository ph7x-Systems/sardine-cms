"""A minimal Sardine CMS theme.

Two files are the whole theme: this one and a stylesheet. Everything
else is five templates that render the context the builder hands them.

The point is not to look good — it is to be readable. Every branch a
real theme would add for a particular section kind is deliberately
absent: one generic loop renders *any* kind, including kinds this theme
has never heard of, which is what the section contract promises.

Copy this directory, rename the package and the entry point, and start
replacing templates one at a time.
"""

from pathlib import Path

from cms_build.themes.jinja import JinjaTheme


class StarterTheme(JinjaTheme):
    """Templates and assets from this package, project overrides on top.

    ``JinjaTheme`` does the environment work: ordered template layers,
    autoescaping, and the project's own ``theme/`` directory taking
    precedence so a site can shadow one template without forking the
    theme (ADR-0007).
    """

    name = "starter"

    def __init__(self, overrides: Path | None = None) -> None:
        super().__init__(layers=("sardine_theme_starter",), overrides=overrides)
