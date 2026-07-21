# ADR-0036 — On-publish webhooks: signed, bounded retries, optional

- **Status:** accepted
- **Date:** 2026-07-21

## Context

The exported site is static; the admin never rebuilds the world on its
own. When content goes live (or leaves the live site), the *host* is
the one that should rebuild — a CI pipeline, a static host's deploy
hook. That handoff needs a push signal: the M7 webhook. The rules in
force apply: optional by construction, environment-only configuration,
no new dependencies, failures never block editorial actions, and
outbound calls carry verifiable authenticity (the receiver must be able
to reject forgeries).

## Decision

- **Two events, the ones that change the public artifact**:
  `published` (a transition into the published status) and
  `unpublished` (a transition out of it — unpublish or archive). Other
  panel activity changes nothing public and emits nothing.
- **Configuration**: `SARDINE_WEBHOOK_URL` (HTTPS required; plain HTTP
  only for loopback addresses, for local development) and
  `SARDINE_WEBHOOK_SECRET`. Both unset means webhooks are off and
  nothing changes anywhere. A configured URL without a secret fails
  startup loudly — unsigned webhooks are not an option.
- **Payload**: minimal JSON —
  `{"event", "entity": {"kind", "id"}, "occurred_at"}` (UTC ISO). No
  content bodies, no titles: the receiver pulls whatever it needs
  through its own channel; the webhook is a doorbell, not a data feed.
- **Signature**: `X-Sardine-Signature: sha256=<hex>` — HMAC-SHA256 of
  the exact request body with the shared secret (standard library).
  The timestamp inside the signed payload lets receivers bound replay.
- **Delivery**: standard-library HTTP, 10-second timeout, from a
  background thread — the editorial response never waits. **Bounded
  retries**: three attempts with increasing backoff, then the failure
  is recorded on the panel's activity state and the event is dropped —
  deliberate: the host's next scheduled build (ADR-0024 recipe) is the
  safety net, and unbounded queues are how systems fall over.

## Consequences

- Trash/restore of published entries goes through unpublish/publish
  transitions where it matters; direct purge does not emit (recorded
  limitation — the scheduled-build recipe covers it).
- Tests stand up a local capture server: signature verified end to end,
  both events, retry on failure, no-config no-op, unsigned-config
  startup failure.
- The receiver contract is documented (ADMIN_GUIDE + wiki): verify the
  signature, respond 2xx quickly, rebuild asynchronously.
