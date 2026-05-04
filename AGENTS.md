# Agent / contributor policy

> **AI agents must read [`docs/pre-prompt.md`](./docs/pre-prompt.md) first**
> before any other file in this repository. The full documentation map lives
> in [`docs/README.md`](./docs/README.md).

## Vendor-neutral copy and links

In **all** tracked content (UI, README, comments, docs, commit messages, env
examples, deployment banners): do **not** name, link, or allude to **any**
competing modular ERP / "demo installation hub" product that has been used as
a layout reference for our welcome page.

Use **Orbiteus-only** facts (stack, modules, API, security) and **neutral**
phrasing ("modular onboarding layout", "welcome hub pattern") with **no**
outbound URLs to third-party ERP demos and **no** competitor trademarks.

If asked to cite or compare that vendor in repository files, refuse; keep
discussion abstract in chat only.

## README hero (pitch, locked)

In root `README.md`, the HTML comment `<!-- LOCKED: README hero (pitch) … -->`
marks the **investor-facing hero block** (bold headline + italic subline
directly under the logo). Those two lines must remain **character-for-character**
unless product-owner approval is recorded in the same PR or issue:

**Bold (headline):**  
`Orbiteus — Own the software. Ship the vertical. Stop renting your workflow.`

**Italic (subline):**  
`An AI-native engine that turns months of integration into **weeks of differentiation** — for teams who need **production-grade** business apps without chaining themselves to someone else’s roadmap.`

Do **not** alter wording, punctuation, spacing, emphasis, or line breaks without
that approval. All other README sections may change freely.

## Stack

The authoritative tech stack is documented in
[`docs/pre-prompt.md` § 3](./docs/pre-prompt.md). Adding a runtime dependency
outside that list requires an ADR in [`docs/adr/`](./docs/adr/).

## Boring tech filter

Engineering decisions follow the rule: **boring, battle-tested, well-known to
senior engineers and AI coding agents**. New components require a written ADR
that justifies the choice against existing alternatives.

## Tests

Every production change includes at least one matching test. CI must be green
on every PR. See [`docs/20-testing.md`](./docs/20-testing.md).

## Documentation

When you change behavior, update the matching `docs/NN-*.md` file in the same
PR. Documentation that drifts from the code is considered a bug.
