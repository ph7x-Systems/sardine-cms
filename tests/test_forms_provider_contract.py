"""The forms provider contract: everything after acceptance.

A provider only ever sees accepted submissions, never answers the
visitor, and is contained when it fails. The fictional provider in
this file registers through an extension and receives a live admin's
submissions — a third destination with zero changes to the endpoint,
the editor or the flow.
"""

from pathlib import Path

import pytest
from cms_core.extensions import Extension
from cms_core.forms import (
    FORMS_CONTRACT_VERSION,
    FormContext,
    FormsProvider,
    FormSubmission,
    available_forms_providers,
    create_forms_provider,
    register_forms_provider,
)
from test_forms_endpoint import GOOD, SENT, _app, _client

RECEIVED: list[tuple[FormSubmission, FormContext]] = []


class LedgerProvider:
    """A fictional destination: it writes every accepted submission to
    an in-memory ledger."""

    contract_version = FORMS_CONTRACT_VERSION

    def handle(self, submission: FormSubmission, form: FormContext) -> None:
        RECEIVED.append((submission, form))


class ExplodingProvider:
    contract_version = FORMS_CONTRACT_VERSION

    def handle(self, submission: FormSubmission, form: FormContext) -> None:
        raise RuntimeError("the queue is gone")


def _ledger_factory() -> LedgerProvider:
    return LedgerProvider()


def _exploding_factory() -> ExplodingProvider:
    return ExplodingProvider()


extension = Extension(name="ledger-forms", forms_providers={"ledger": _ledger_factory})


def _provider_app(tmp_path: Path, name: str) -> object:
    app = _app(tmp_path)
    toml = (tmp_path / "sardine.toml").read_text(encoding="utf-8")
    (tmp_path / "sardine.toml").write_text(toml + f'provider = "{name}"\n', encoding="utf-8")
    return app


def test_an_extension_provider_receives_accepted_submissions(tmp_path: Path) -> None:
    register_forms_provider("ledger", _ledger_factory)  # what activation does
    RECEIVED.clear()
    with _client(_provider_app(tmp_path, "ledger")) as client:  # type: ignore[arg-type]
        ok = client.post("/forms/submit", data=GOOD)
        bad = client.post("/forms/submit", data={**GOOD, "field_name": ""})
        spam = client.post("/forms/submit", data={**GOOD, "website": "x"})
    assert (ok.status_code, bad.status_code, spam.status_code) == (200, 422, 403)
    assert len(RECEIVED) == 1  # only the accepted one reached the provider
    submission, form = RECEIVED[0]
    assert submission.values["name"] == "Ana"
    assert form.heading == "Write to the fleet"
    assert form.notify == "owner@example.com"
    assert not SENT  # the reference legs stood down


def test_a_provider_failure_is_contained_and_audited(tmp_path: Path) -> None:
    from cms_core import create_storage

    register_forms_provider("exploding", _exploding_factory)
    with _client(_provider_app(tmp_path, "exploding")) as client:  # type: ignore[arg-type]
        response = client.post("/forms/submit", data=GOOD)
    assert response.status_code == 200  # never visitor-facing
    with create_storage(f"sqlite:///{tmp_path / 'content.db'}") as storage:
        actions = [record.action for record in storage.list_activity(limit=10)]
    assert "form-provider-failed" in actions


def test_selection_validates_the_contract() -> None:
    with pytest.raises(ValueError, match="unknown forms provider 'nowhere'"):
        create_forms_provider("nowhere")

    class Ancient:
        contract_version = 0

        def handle(self, submission: FormSubmission, form: FormContext) -> None: ...

    register_forms_provider("contract-ancient", lambda: Ancient())
    with pytest.raises(ValueError, match="contract version 0"):
        create_forms_provider("contract-ancient")

    class Hollow:
        contract_version = FORMS_CONTRACT_VERSION

    register_forms_provider("contract-hollow", lambda: Hollow())
    with pytest.raises(ValueError, match="does not implement the forms contract"):
        create_forms_provider("contract-hollow")

    register_forms_provider("ledger", _ledger_factory)  # idempotent by identity
    with pytest.raises(ValueError, match="already registered differently"):
        register_forms_provider("ledger", lambda: LedgerProvider())
    provider = create_forms_provider("ledger")
    assert isinstance(provider, FormsProvider)
    assert "ledger" in available_forms_providers()


def test_extension_activation_registers_the_provider(tmp_path: Path) -> None:
    """The dotted-path activation used by real projects registers the
    provider exactly like deploy providers — zero core changes."""
    from cms_cli.project import load_project

    (tmp_path / "sardine.toml").write_text(
        '[site]\nname = "S"\nbase_url = "https://s.example"\nlanguages = []\n'
        'extensions = ["test_forms_provider_contract:extension"]\n',
        encoding="utf-8",
    )
    project = load_project(tmp_path)
    project.load_extensions()
    assert "ledger" in available_forms_providers()
