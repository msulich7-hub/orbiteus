# 24 — Tree Spec: Admin UI

> Source of truth for admin UI status. Last reviewed: 2026-05-03.

## 1. Foundation — DONE

- [x] Next.js 16 App Router + React 19 + Mantine 9
- [x] axios with Bearer token + 401 redirect
- [x] ui-config fetcher + cache (`lib/modelConfig.ts`)
- [x] XML view arch parser (`lib/viewParser.ts`)
- [x] Branding context provider
- [x] `next.config.js` `/api/*` proxy

## 2. Layout

- [x] AppShell with sidebar + header + content area
- [x] Dynamic sidebar from ui-config
- [x] Header with branding, ⌘K, user menu
- [x] Login page (JWT flow)
- [x] Welcome page (`/login` route currently — to be split)
- [ ] Split: `/welcome` (public) + `/login` (form) + `/` (dashboard)
- [ ] Responsive sidebar collapse on mobile/tablet
- [ ] Breadcrumbs Module > Model > Record name
- [ ] Dashboard with stats widgets

## 3. Widget registry

- [x] text, email, tel, number, textarea, boolean, date, select (static)
- [ ] select with `optionsResource` (dynamic API options)
- [ ] many2one (resolved name from `{field}__name`)
- [ ] badge (status colors)
- [ ] monetary (locale + currency formatting)
- [ ] statusbar (form header step indicator)
- [ ] tags (TagsInput)
- [ ] readonly attribute enforcement
- [ ] date display formatter in list views
- [ ] Widget registry exported from `admin-ui/src/orbiteus-ui/widgets`

## 4. List view

- [x] ResourceList with columns from ui-config
- [x] Search via `?name__contains=`
- [x] Server-side sorting
- [x] Pagination
- [x] Per-row delete with confirm
- [x] "New" button → create form
- [ ] Column widget rendering (badge, monetary, date, many2one)
- [ ] Bulk actions (select N → delete / export CSV)
- [ ] Quick filters bar
- [ ] Empty state with illustration + "Create first" CTA

## 5. Form view

- [x] ResourceForm with fields from ui-config / XML
- [x] Create + edit modes
- [x] Client + server validation
- [x] Delete in edit mode
- [ ] `<group>` sections from XML
- [ ] Many2one searchable select
- [ ] Statusbar at the top of form
- [ ] Readonly fields disabled
- [ ] Tabs (Details / Notes / History)

## 6. Kanban / Calendar / Other views

- [x] Kanban board with drag-drop, optimistic updates
- [x] ViewSwitcher (?view=)
- [ ] Kanban card enhancement (badge, monetary, avatar)
- [ ] Calendar view (monthly + weekly, dayjs based)
- [ ] Graph view (bar/line/pie via recharts)
- [ ] Pivot — deferred
- [ ] Activities timeline — deferred

## 7. Command Palette

- [x] ⌘K modal
- [x] Debounced search → `/api/ai/actions`
- [x] Grouped results
- [x] Keyboard navigation
- [x] English labels + multilingual keywords
- [ ] Recent actions section (localStorage)
- [ ] Smart Search prefix (`?`) — deferred

## 8. AI integration in UI

- [ ] `<PromptInput>` widget exported from `admin-ui/src/orbiteus-ui`
- [ ] `<AIChatPanel>` (sidebar / drawer)
- [ ] `<AIDashboard>` for prompt-driven charts
- [ ] `useAIContext(model, id)` hook
- [ ] Graceful fallback when `ir_ai_credential` absent
- [ ] BYOK admin page (`/admin/ai-credentials`)

## 9. Notifications and errors

- [ ] Toast on create/update/delete success
- [ ] Toast on API error (red)
- [ ] 403 / 404 / network error handlers
- [ ] Form-level error banner

## 10. Cleanup of hardcoded pages

- [ ] Remove `app/crm/customers`, `opportunities`, `pipelines` (use catch-all)
- [ ] Remove `app/base/companies`, `partners`, `users`
- [ ] Remove `app/technical/*` (use catch-all)
- [ ] Remove legacy components flagged deprecated
- [ ] Translate remaining Polish strings to English

## 11. Responsive

- [ ] Sidebar collapsible on tablet, hidden on mobile + burger
- [ ] Tables horizontal scroll on small screens
- [ ] Forms single column mobile, two columns desktop
- [ ] Kanban horizontal scroll on mobile

## 12. Tests

- [ ] Vitest + RTL setup
- [ ] viewParser tests
- [ ] modelConfig tests
- [ ] ResourceList component tests
- [ ] ResourceForm component tests
- [ ] CommandPalette tests
- [ ] Playwright E2E: login → create → edit → delete
