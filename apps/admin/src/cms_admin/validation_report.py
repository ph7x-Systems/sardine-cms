"""Shared validation-report context for the dashboard and publishing pages.

The report is rendered by ``templates/_validation_report.html.j2``: the gate
callout, one row per rule (passing rules included — the report must show what
ran, not only what failed) and the issue list with subjects linked to their
edit screens.
"""

from dataclasses import dataclass

from cms_core import SOURCE_LANGUAGE, TARGET_LANGUAGES, Language
from cms_validation import (
    Issue,
    Report,
    RuleSet,
    SiteContent,
    ValidationContext,
    default_ruleset,
)


@dataclass(frozen=True, slots=True)
class FindingGroup:
    """One finding as a reader meets it: the same rule saying the same
    thing about the same subject, in however many languages.

    A five-language project reports a title-length hint five times over —
    identical severity, rule, subject and message, differing only in the
    language tag. Five rows carry no more information than one row with
    five tags, and they cost the reader five times the reading.
    """

    code: str
    severity: str
    subject: str
    message: str
    languages: tuple[str, ...]
    count: int


def group_issues(issues: list[Issue]) -> list[FindingGroup]:
    """Collapse issues that differ only by language, keeping first-seen
    order so the report still reads in the order the rules ran."""
    order: list[tuple[str, str, str, str]] = []
    languages: dict[tuple[str, str, str, str], list[str]] = {}
    counts: dict[tuple[str, str, str, str], int] = {}
    for issue in issues:
        key = (issue.code, issue.severity.value, issue.subject, issue.message)
        if key not in counts:
            order.append(key)
            languages[key] = []
            counts[key] = 0
        counts[key] += 1
        if issue.language is not None:
            languages[key].append(issue.language.value)
    return [
        FindingGroup(
            code=code,
            severity=severity,
            subject=subject,
            message=message,
            languages=tuple(languages[key]),
            count=counts[key],
        )
        for key in order
        for code, severity, subject, message in (key,)
    ]


def run_report(
    content: SiteContent,
    languages: tuple[Language, ...],
    extra_rules: tuple[object, ...] = (),
    source_language: Language = SOURCE_LANGUAGE,
    disabled: tuple[str, ...] = (),
) -> Report:
    rules = default_ruleset()
    rules.extend(extra_rules)  # type: ignore[arg-type]  # ADR-0028 extensions
    return RuleSet(rules=rules, disabled=set(disabled)).run(
        content,
        ValidationContext(required_languages=languages, source_language=source_language),
    )


def report_context(
    content: SiteContent,
    languages: tuple[Language, ...] | None = None,
    extra_rules: tuple[object, ...] = (),
    source_language: Language = SOURCE_LANGUAGE,
    disabled: tuple[str, ...] = (),
) -> dict[str, object]:
    required = languages or TARGET_LANGUAGES
    report = run_report(
        content, tuple(required), extra_rules, source_language=source_language, disabled=disabled
    )
    scope = {
        "articles": len(content.articles),
        "pages": len(content.pages),
        "media": len(content.media),
        # +1: the source language on top of the required translations.
        "languages": len(required) + 1,
    }
    subject_links: dict[str, str] = {}
    for issue in report.issues:
        kind, _, rest = issue.subject.partition(":")
        ident = rest.split("/", 1)[0]
        if kind == "article":
            subject_links[issue.subject] = f"/articles/{ident}"
        elif kind == "page":
            subject_links[issue.subject] = f"/pages/{ident}"
        elif kind == "media":
            subject_links[issue.subject] = "/media"
    # A bounded summary for surfaces that must not list every finding:
    # rule -> how many, most first. The dashboard shows this and links to
    # the publishing screen, which owns the filtered, paginated table.
    tally: dict[str, int] = {}
    for issue in report.issues:
        tally[issue.code] = tally.get(issue.code, 0) + 1
    issue_counts = sorted(tally.items(), key=lambda pair: (-pair[1], pair[0]))
    return {
        "report": report,
        "scope": scope,
        "subject_links": subject_links,
        "issue_counts": issue_counts,
    }
