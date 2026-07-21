"""Locales (ADR-0034 phase 1): validated tags behind the enum's old surface.

``Language`` is an interned, validated ``str`` subclass. Everything the
old five-member enum offered still holds: identity comparisons
(``language is Language.EN``), ``.value``, class iteration, equality
with plain strings, and ``Language(tag)`` raising ``ValueError`` for
anything unregistered. What opens up is the set itself:
``Language.register(tag)`` admits any well-formed lowercase BCP-47-style
tag — the entry point language packs use in the later ADR-0034 phases.
Until a pack registers a tag, behavior is byte-for-byte what it was.
"""

import re
from typing import Any, ClassVar

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

TAG_PATTERN = re.compile(r"[a-z]{2,3}(-[a-z0-9]{2,8})*")


class _LanguageMeta(type):
    """Class-level iteration, as the enum offered (``for l in Language``)."""

    def __iter__(cls) -> "Any":
        return iter(cls._registered.values())  # type: ignore[attr-defined]


class Language(str, metaclass=_LanguageMeta):
    """A registered locale tag; instances are interned, so identity
    comparisons behave exactly like enum members."""

    _registered: ClassVar[dict[str, "Language"]] = {}

    EN: ClassVar["Language"]
    PT_PT: ClassVar["Language"]
    ES: ClassVar["Language"]
    FR: ClassVar["Language"]
    DE: ClassVar["Language"]

    def __new__(cls, tag: object) -> "Language":
        if isinstance(tag, Language):
            return tag
        text = str(tag)
        registered = cls._registered.get(text)
        if registered is None:
            raise ValueError(f"{text!r} is not a registered language")
        return registered

    @classmethod
    def register(cls, tag: str) -> "Language":
        """Admit a locale tag (ADR-0034). Idempotent; validates shape."""
        existing = cls._registered.get(tag)
        if existing is not None:
            return existing
        if not TAG_PATTERN.fullmatch(tag):
            raise ValueError(f"invalid language tag {tag!r}")
        instance = str.__new__(cls, tag)
        cls._registered[tag] = instance
        return instance

    @property
    def value(self) -> str:
        return str(self)

    def __repr__(self) -> str:
        return f"Language({str(self)!r})"

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: type, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls,
            core_schema.str_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(str),
        )


Language.EN = Language.register("en")
Language.PT_PT = Language.register("pt-pt")
Language.ES = Language.register("es")
Language.FR = Language.register("fr")
Language.DE = Language.register("de")

SOURCE_LANGUAGE = Language.EN
TARGET_LANGUAGES: tuple[Language, ...] = tuple(
    language for language in Language if language is not SOURCE_LANGUAGE
)
