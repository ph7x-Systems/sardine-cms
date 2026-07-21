"""The open locale type (ADR-0034 phase 1): the enum surface, provable."""

import pickle

import pytest
from cms_core import Language
from cms_core.languages import SOURCE_LANGUAGE, TARGET_LANGUAGES
from pydantic import BaseModel


def test_the_enum_surface_is_intact() -> None:
    assert Language("en") is Language.EN
    assert Language(Language.EN) is Language.EN
    assert Language.EN.value == "en"
    assert Language.EN == "en"
    assert [language.value for language in Language][:5] == ["en", "pt-pt", "es", "fr", "de"]
    assert SOURCE_LANGUAGE is Language.EN
    assert Language.EN not in TARGET_LANGUAGES
    assert len(TARGET_LANGUAGES) >= 4


def test_unregistered_tags_raise_exactly_like_the_enum_did() -> None:
    with pytest.raises(ValueError):
        Language("xx-not-registered")


def test_register_opens_the_set_idempotently() -> None:
    first = Language.register("gl")
    assert Language("gl") is first
    assert Language.register("gl") is first
    assert first == "gl" and first.value == "gl"


def test_register_validates_the_tag_shape() -> None:
    for bad in ("PT-PT", "en_US", "", "e", "en--x", "en-", "português"):
        with pytest.raises(ValueError):
            Language.register(bad)


def test_pydantic_fields_and_dict_keys_round_trip() -> None:
    class Model(BaseModel):
        lang: Language
        alts: dict[Language, str]

    model = Model(lang="pt-pt", alts={"en": "A", "de": "B"})
    assert model.lang is Language.PT_PT
    assert set(model.alts) == {Language.EN, Language.DE}
    assert Model.model_validate_json(model.model_dump_json()) == model


def test_pickle_preserves_interning() -> None:
    assert pickle.loads(pickle.dumps(Language.PT_PT)) is Language.PT_PT
