"""Page/section translation aggregation and publishing gate."""

import pytest
from cms_core import (
    Language,
    Page,
    PageContent,
    Section,
    SectionContent,
    TranslationState,
    new_page,
)


def make_page_with_hero() -> tuple[Page, Section]:
    page = new_page("home", PageContent(title="Home", slug="home"))
    hero = Section(
        key="hero",
        kind="hero",
        source=SectionContent(fields={"heading": "Welcome"}, media=["hero-image"]),
    )
    page.sections.append(hero)
    return page, hero


def test_page_state_aggregates_sections_worst_state() -> None:
    page, hero = make_page_with_hero()
    page.set_translation(Language.PT_PT, PageContent(title="Início", slug="inicio"))

    # Page content is translated but the hero section is not: page is missing.
    assert page.translation_state(Language.PT_PT) is TranslationState.MISSING

    hero.set_translation(Language.PT_PT, SectionContent(fields={"heading": "Bem-vindo"}))
    assert page.translation_state(Language.PT_PT) is TranslationState.COMPLETE

    # Editing the section source downgrades the aggregate to outdated.
    hero.source = SectionContent(fields={"heading": "Welcome!"}, media=["hero-image"])
    assert page.translation_state(Language.PT_PT) is TranslationState.OUTDATED
    assert not page.can_publish(required_languages=(Language.PT_PT,))


def test_page_without_own_translation_is_missing_even_if_sections_translated() -> None:
    page, hero = make_page_with_hero()
    hero.set_translation(Language.ES, SectionContent(fields={"heading": "Bienvenido"}))
    assert page.translation_state(Language.ES) is TranslationState.MISSING


def test_section_checksum_is_order_insensitive_for_fields() -> None:
    first = SectionContent(fields={"a": "1", "b": "2"})
    second = SectionContent(fields={"b": "2", "a": "1"})
    assert first.checksum() == second.checksum()


def test_section_checksum_changes_with_media() -> None:
    without = SectionContent(fields={"a": "1"})
    with_media = SectionContent(fields={"a": "1"}, media=["logo"])
    assert without.checksum() != with_media.checksum()


def test_section_lookup_by_key() -> None:
    page, hero = make_page_with_hero()
    assert page.section("hero") is hero
    assert page.section("nope") is None


def test_page_slug_must_be_a_slug() -> None:
    with pytest.raises(ValueError):
        PageContent(title="Home", slug="Not A Slug!")
