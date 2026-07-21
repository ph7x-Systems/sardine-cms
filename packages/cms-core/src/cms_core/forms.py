"""Form submissions (ADR-0039): optionally stored, never load-bearing.

Storage is a consumer of an accepted submission — the endpoint
validates, accepts and answers whether or not persistence is
configured, and a storage failure never reaches the visitor. The
operational fields (when, which form, which language) are queryable;
the visitor's values are an opaque payload — the schema never depends
on user-defined field keys.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class FormSubmission:
    id: str
    received_at: datetime
    page_id: str
    section_key: str
    language: str
    values: dict[str, str] = field(default_factory=dict)


FORMS_CONTRACT_VERSION = 1
"""The provider contract's version: validated at selection time, never
mid-submission."""


@dataclass(frozen=True, slots=True)
class FormContext:
    """What the addressed form declared — providers need no
    configuration lookups of their own."""

    heading: str
    notify: str = ""
    store: bool = False


@runtime_checkable
class FormsProvider(Protocol):
    """Everything after acceptance (ADR-0040): deliver, store, forward.

    The endpoint owns the protocol, the spam layers, validation and
    the visitor's answer; whatever ``handle`` raises is contained and
    audited there — a provider can never break the response contract.
    """

    contract_version: int

    def handle(self, submission: FormSubmission, form: FormContext) -> None: ...


_PROVIDERS: dict[str, object] = {}


def register_forms_provider(name: str, factory: object) -> None:
    """Register a factory ``() -> FormsProvider``. Idempotent by
    identity; loud on conflict."""
    existing = _PROVIDERS.get(name)
    if existing is not None and existing is not factory:
        raise ValueError(f"forms provider {name!r} is already registered differently")
    _PROVIDERS[name] = factory


def available_forms_providers() -> tuple[str, ...]:
    return tuple(sorted(_PROVIDERS))


def create_forms_provider(name: str) -> FormsProvider:
    """Resolve and build the configured provider, validating the
    contract before anything runs."""
    factory = _PROVIDERS.get(name)
    if factory is None:
        known = ", ".join(available_forms_providers()) or "none"
        raise ValueError(f"unknown forms provider {name!r} (registered: {known})")
    provider = factory()  # type: ignore[operator]
    version = getattr(provider, "contract_version", None)
    if version != FORMS_CONTRACT_VERSION:
        raise ValueError(
            f"provider {name!r} implements contract version {version!r}; "
            f"this CMS speaks version {FORMS_CONTRACT_VERSION}"
        )
    if not isinstance(provider, FormsProvider):
        raise ValueError(f"provider {name!r} does not implement the forms contract")
    return provider
