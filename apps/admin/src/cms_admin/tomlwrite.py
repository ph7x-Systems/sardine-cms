"""Writing values into ``sardine.toml`` safely.

The panel edits the project file as text (surgical writes, comments and
ordering preserved), so every value it embeds has to be a valid TOML
basic string. A Windows path is the case that proved it: `C:\\Users\\…`
contains `\\U`, which TOML reads as a Unicode escape, and the file the
panel had just written could no longer be parsed.
"""

_ESCAPES = {
    "\\": "\\\\",
    '"': '\\"',
    "\b": "\\b",
    "\t": "\\t",
    "\n": "\\n",
    "\f": "\\f",
    "\r": "\\r",
}


def toml_string(value: object) -> str:
    """``value`` as a quoted TOML basic string, escapes included."""
    text = str(value)
    return '"' + "".join(_ESCAPES.get(char, char) for char in text) + '"'
