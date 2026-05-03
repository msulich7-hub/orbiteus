# 01 — Engine Positioning

## What Orbiteus is

Orbiteus is an **engine** for AI-native business apps. It sits between a pure
framework and a finished product:

| Category | Example | Provides |
|---|---|---|
| Framework (pure) | Flask, Express | Abstractions only — devs build everything |
| Batteries-included framework | Django, Rails | + ORM, auth, admin scaffolding |
| **Engine** | **Orbiteus**, Laravel + Filament, Odoo | + UI shell, RBAC, multitenancy, AI/realtime/audit, **one canonical product example** |
| Product | Salesforce, HubSpot | Ready SaaS, customization through configuration |

Orbiteus ships:

- A **framework layer** (`orbiteus_core`, `modules/base`, `modules/auth`).
- An **AI layer** (providers, BYOK, tools, embeddings, prompts, dashboards).
- A **canonical product example** (`modules/crm` with Person / Lead / Stage / Team).
- Two front-ends (`admin-ui` for internal users, `portal-ui` for external partners)
  built on a shared design system (`packages/ui` on top of Mantine 8).

The promise: a senior engineer cloning the repo and running `docker compose up`
gets a production-grade skeleton (auth, RBAC, audit, AI, realtime) and a working
CRM in minutes — saving 3–4 months of plumbing per project.

## Where the boundary runs

| Layer | Belongs in framework | Does not belong |
|---|---|---|
| `orbiteus_core` | Module Registry, BaseRepository, AutoRouter, ui-config, JWT, RBAC, audit, EventBus, Outbox, Cache, Realtime, AI provider abstraction, sequences, attachments, mail engine, report engine | A specific Customer / Invoice / Department model |
| `modules/base` | `users`, `roles`, `companies`, `tenants`, all `ir_*` system tables (model_access, rule, sequence, attachment, message, activity, cron, audit_log, embedding, ai_credential, outbox) | Sales pipelines, employees, projects |
| `modules/auth` | JWT login/refresh/2FA, password reset, share-link tokens (portal scope) | Onboarding to a specific product |
| `modules/crm` *(canonical example)* | Person, Lead, Stage, Team, demo `actions.py` and `ai.py` | Industry-specific extensions |
| `modules/hr`, `project`, `social` *(samples)* | Optional reference modules — can be deleted in client deployments | Same as above |
| `admin-ui` | AppShell, dynamic renderer, widget registry, branding, ⌘K, AI chat panel | Per-module hardcoded TSX pages |
| `portal-ui` | Public layout, share-link entry, RBAC-scoped resource views (read + comments) | Internal CRM / HR navigation |

## Canonical example policy

The CRM-MVP module **ships with the engine** and is maintained as a first-class
demo. It has three jobs:

1. Prove that a single module can deliver List, Kanban, and Calendar views
   without per-module TSX.
2. Show how `ai.py` plugs an AI assistant into a domain.
3. Exercise the framework's audit, realtime, and queue paths end-to-end.

CRM is **not** the framework. Client deployments can disable it (`modules/crm`
removed from `registry.register(...)`) without affecting the engine.

## Versioning impact

- A breaking change in **framework layer** requires a major version bump and an ADR.
- A breaking change in **canonical example** requires a minor bump and a migration note.
- Sample modules (`hr`, `project`, `social`) can change at any time — no SLA.

See `21-release-and-versioning.md`.

## When to create a new module vs extend an existing one

Create a new module when:

- The domain is independent (its own RBAC matrix, its own data model).
- It would otherwise force cross-module imports.
- Its data should be optional in some deployments.

Extend an existing module when:

- You add fields, actions, or views to existing models.
- The change does not introduce a new aggregate root.

If unsure, propose a module first and ask the user.
