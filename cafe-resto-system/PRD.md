Below is a **very detailed PRD v1** designed specifically to be executed by an **LLM-driven multi-agent development workflow** (parallelizable, clear boundaries, clear artifacts, clear tests). It reflects your locked decisions:

* **Web-first** SaaS (PWA)
* **Multi-tenant**, **multi-location**, **multi-warehouse** (simple stock initially)
* **QR table ordering = Draft-first ALWAYS** (no presence token / no direct-to-kitchen)
* **Waiter handheld confirms** drafts (can edit + upsell + course control)
* Guests can **edit drafts before waiter starts review**
* Printing via **Ethernet/Wi-Fi network printers**
* Payments: **cash + external terminal capture** first, plus **pay-at-table via QR**
* HQ admin + store managers (scoped permissions)

---

# PRD v1 — “Hospitality OS (Draft-first QR)”

**Version:** 1.0
**Date:** 2026-01-03
**Target region:** Argentina first (fiscal optional phase)
**Primary business model:** SaaS with per-tenant configuration + extensions

## 0) Product principles (non-negotiables)

1. **Draft-first ordering:** Guest actions never create kitchen tickets directly. A staff user must confirm.
2. **Offline-first operations:** POS + waiter + KDS must keep functioning if cloud is down (at minimum: local continuity on each device; optional LAN relay later).
3. **Zero-chaos kitchen:** Only confirmed orders generate tickets; coursing defaults to **Drinks first**.
4. **Multi-location native:** Org → locations → registers/stations/tables/warehouses.
5. **Auditability:** Every sensitive action is logged (voids, reassign table, confirm orders, refunds).

---

# 1) Goals, success metrics, scope

## 1.1 Goals

* Reduce waiter time spent “taking orders” by shifting entry to guests (draft), while preserving service quality and kitchen correctness.
* Provide a single platform: **Waiter handheld + POS + KDS + Admin + QR guest**.
* Enable multi-location scaling and per-tenant customization safely.

## 1.2 Success metrics (launch KPIs)

* **Time-to-confirm**: median time from guest “Call waiter” to waiter confirm < 3 minutes
* **Order error rate**: < 1% confirmed orders require staff correction after firing
* **Kitchen ticket integrity**: 0 duplicate tickets from sync/retry
* **Uptime**: service continues in degraded mode during cloud outage (POS/waiter can still operate locally)

## 1.3 In-scope (v1)

* Multi-tenant auth + RBAC (HQ admin vs location manager vs waiter vs kitchen)
* Menu/catalog, modifiers, taxes, price rules (basic)
* Tables/floorplan + waiter handheld
* Guest QR draft app (PWA)
* Draft lifecycle + collaboration (edit until review lock)
* Confirm → tickets (BAR + KITCHEN) with **courses** (drinks first)
* KDS station screens + Expo
* POS checkout: cash + external terminal capture; pay-at-table QR
* Reporting (sales, items, staff activity)
* Printing to network printers (receipt + kitchen tickets)

## 1.4 Out of scope (explicitly deferred)

* Payroll
* Deep accounting ERP
* Direct-to-kitchen guest ordering (intentionally excluded)
* Complex recipe/ingredient costing (simple stock only in v1 inventory phase)
* Full delivery aggregator integrations (phase later)

---

# 2) Personas & roles

## 2.1 Personas

* **HQ Admin (Org Owner):** manages org, locations, global settings, enterprise reporting, integrations
* **Location Manager:** manages one location, staff, void approvals, shift closes, local menu overrides
* **Waiter:** table service, drafts inbox, confirm + coursing, payments (optional)
* **Cashier:** fast checkout, receipts, refunds (restricted)
* **Bar/Kitchen Staff:** station KDS, bump items, mark ready
* **Expo:** sees all tickets, manages course firing, resolves issues
* **Guest:** scans QR, drafts order, edits draft, requests confirmation, pays by QR

## 2.2 RBAC (permission examples)

* `draft:view`, `draft:confirm`, `draft:reject`, `draft:reassign_table`
* `order:create`, `order:fire_course`, `order:void_item`, `order:discount`
* `payment:record_cash`, `payment:record_external`, `payment:refund` (manager only)
* `menu:edit`, `pricing:edit`, `tables:edit`, `reports:view_sensitive`
* Scope dimension: `org_scope`, `location_scope`, `section_scope`

---

# 3) Product modules

1. **Guest QR App (PWA)** — Draft builder + edit + “Call waiter” + pay by QR
2. **Waiter Handheld App (PWA)** — Draft inbox + edit + confirm + course control + table mgmt
3. **POS App (PWA)** — Walk-in orders + checkout + printing + shift close
4. **KDS App (PWA)** — Station filtering + ticket states + Expo view
5. **Admin Backoffice (Web)** — catalog, staff, permissions, tables, reports, settings
6. **Core Services (API)** — tenancy, auth, orders, drafts, tickets, payments, reporting
7. **Optional Local Print Bridge** — for universal printer support (optional, recommended for wide compatibility)

---

# 4) Core workflows (end-to-end)

## 4.1 Guest → Draft → Waiter Confirm → Bar (Drinks) → Kitchen (Food)

**Default coursing:** Drinks fired on confirm; food held until later fire.

**Steps**

1. Guest scans QR at table → opens **Table Session**
2. Guest creates Draft (OPEN), adds items/modifiers, notes
3. Guest taps **Call waiter** (SUBMITTED)
4. Guest may edit draft and press **Update order** (UPDATED)
5. Waiter sees drafts inbox: “Table 12 — Updated”
6. Waiter opens draft → status becomes **IN_REVIEW** (guest edits locked)
7. Waiter confirms + edits final items + chooses: **Confirm & Fire Drinks**
8. System creates **Check + Order**, generates **BAR ticket** for drinks (immediate)
9. Later: waiter/expo fires **MAINS** course → kitchen ticket created
10. KDS updates statuses; ready signals flow back to waiter/POS

## 4.2 Draft collaboration (guest can edit before waiter arrives)

* Guest edits allowed in OPEN/SUBMITTED/UPDATED
* Guest edits blocked in IN_REVIEW (waiter lock)
* Confirm creates immutable “snapshot” of draft at confirm time

## 4.3 Pay at table (QR payment)

* Guest sees “Pay now” on table session once check exists
* Payment intent created for total (tip optional)
* QR displayed to guest (Mercado Pago flow in later implementation)
* Webhook updates `PAID` → closes check → prints receipt optional

## 4.4 POS walk-in order (no table)

* POS creates order directly (counter service)
* Optionally still uses coursing but typically “send all”
* Checkout with cash/external capture

---

# 5) Draft-first ordering specification (the heart)

## 5.1 Entities

* **TableSession**: `{session_id, tenant_id, location_id, table_id, created_at, expires_at}`
* **DraftOrder**: `{draft_id, table_session_id, status, version, last_submitted_at, last_updated_at}`
* **DraftLineItem** + modifiers + notes
* **DraftLock**: `{draft_id, lock_owner_user_id, lock_expires_at}`

## 5.2 Draft states

* `OPEN` — not yet requested
* `SUBMITTED` — “Call waiter” pressed (visible to waiter inbox)
* `UPDATED` — edits after submit + “Update order” pressed (notifies waiter)
* `IN_REVIEW` — waiter opened; guest edits blocked
* `CONFIRMED` — converted into check/order
* `REJECTED` — rejected by staff (with reason)
* `EXPIRED` — TTL reached; auto removed/archived

## 5.3 Versioning & locking rules

* **Optimistic concurrency:** each update includes `expected_version`
* Server increments version on successful update
* Waiter lock acquisition sets `IN_REVIEW` and lock TTL (e.g., 120s auto-renew while active)
* If lock expires, draft returns to `SUBMITTED/UPDATED` depending on last action

## 5.4 Waiter inbox rules (noise control)

* Only drafts with `status in {SUBMITTED, UPDATED}` appear
* Rate limits:

  * max active drafts per table session: 2
  * cooldown after rejection: e.g., 2 minutes
* “Updated” badge when version changes after submit

## 5.5 Confirm behavior

On confirm:

* Create **Check** (if none exists) or attach to existing open check
* Create **Order** object with confirmed snapshot
* Generate **tickets**:

  * `DRINKS` → BAR station tickets created immediately
  * `FOOD` courses → created as held tickets or pending items (depending on KDS design)
* Emit audit event: `DraftConfirmed`

## 5.6 Reject behavior

* Waiter chooses reason: “No guest found”, “Wrong table”, “Spam”, “Kitchen closed”, etc.
* Guest sees friendly message + can open a new draft

---

# 6) Coursing & stations (bar/kitchen)

## 6.1 Courses

Default course set (configurable per tenant/location):

* `DRINKS` (auto-fire on confirm)
* `APPETIZERS`
* `MAINS`
* `DESSERT`

## 6.2 Station routing

Each menu item is mapped to:

* `station = BAR | KITCHEN | ...`
* `course = DRINKS|MAINS|...`
* optional `prep_time_hint`

Ticket generation rules:

* On confirm, create tickets only for fired courses
* Non-fired courses are staged; firing later generates tickets

## 6.3 Expo mode

* View all tickets across stations
* Ability to fire next course
* Ability to resolve: move item station (manager only), reprint ticket, add note

---

# 7) Printing (Ethernet/Wi-Fi printers)

## 7.1 Requirements

* Print receipts (customer + merchant copy)
* Print kitchen/bar tickets (optional if KDS used; many still want backup print)
* Reprint, void print, end-of-day summary

## 7.2 Supported approaches (choose per installation)

**Path A (recommended for broad compatibility): Optional Local Print Bridge**

* A small local service receives print jobs (HTTPS) and prints via:

  * raw ESC/POS
  * PDF
* Benefits: supports many printers, avoids browser limitations

**Path B (model-specific “pure web” printing)**

* Specific printer ecosystems that support browser workflows (vendor SDK/polling)
* Documented as “supported hardware list”

## 7.3 Printer configuration

* Location has printer profiles:

  * Receipt printer
  * Bar printer
  * Kitchen printer
* Each station can have 0..n printers
* IP + port + protocol + template

## 7.4 Print templates

* Receipt template: legal name, CUIT, address, tax info (fiscal phase later), order lines, taxes, totals, payment method
* Kitchen template: table, course, modifiers, notes, timestamps, QR order id

---

# 8) Payments (Phase-structured)

## 8.1 Payment methods (v1)

* **Cash**
* **External terminal capture** (Payway / Mercado Pago Point handled outside; we store reference)
* **Pay at table QR** (Mercado Pago integration phase; still in v1 scope as module)

## 8.2 Payment entities

* `PaymentIntent` (amount, currency, status)
* `Payment` (method, reference, captured_at)
* `Refund` (manager only)
* `Tip` (optional; rules per location)

## 8.3 Reconciliation

* Shift close:

  * cash counted vs expected
  * external captured total vs expected
* Mandatory reason codes for discrepancies

---

# 9) Multi-location + multi-warehouse (simple stock)

## 9.1 Location model

* Org has many locations
* Each location has:

  * tables/floors
  * registers
  * stations
  * printers
  * warehouse(s)

## 9.2 Warehouse model (simple stock)

* `Warehouse` (location-scoped or central)
* `StockItem` (SKU, unit, reorder threshold)
* `StockMovement` types:

  * RECEIVE (vendor)
  * SELL (optional linkage to items sold)
  * TRANSFER_OUT / TRANSFER_IN
  * ADJUSTMENT

## 9.3 Transfers

* `Transfer` has `from_warehouse`, `to_warehouse`, status: `CREATED → IN_TRANSIT → RECEIVED`

---

# 10) Admin Backoffice

## 10.1 Menu management

* categories, items, modifiers
* availability (86)
* station/course mapping per item
* price rules (happy hour later if needed)

## 10.2 Staff management

* users, roles, permissions
* location assignment
* section assignment for waiters

## 10.3 Tables/floors

* floor plan editor (drag/drop)
* table metadata (seats, section)

## 10.4 Reporting (v1)

* sales by hour/day
* top items
* drafts stats (submitted/confirmed/rejected)
* staff activity (confirm counts, voids, discounts)

---

# 11) SaaS customization model (safe per-tenant)

You asked how to avoid tenant-specific changes affecting others.

## 11.1 Configuration-first

* Feature flags per tenant/location
* Policy rules:

  * confirm required (always true in our product)
  * which courses exist
  * default course auto-fire behavior
  * rejection reasons list

## 11.2 Custom fields (no schema changes)

* For extensions: `custom_fields` JSON per entity with validation rules stored in config
* Access controlled per role

## 11.3 Plugins/webhooks (later but planned now)

* Outbound webhooks:

  * `draft.submitted`, `draft.confirmed`, `ticket.ready`, `payment.paid`
* Tenant-specific endpoints with signing + retries + rate limits
* This covers “custom things” without DB migrations

---

# 12) Non-functional requirements

## 12.1 Performance

* Waiter inbox loads < 1s for 200 active tables
* KDS updates < 300ms within same location (target)

## 12.2 Reliability

* Idempotent APIs (retries never duplicate orders/tickets/payments)
* Audit log for critical actions

## 12.3 Security

* Tenant isolation mandatory
* RBAC enforced server-side
* Rate limiting for guest endpoints
* CSRF protection, secure cookies, device session controls

## 12.4 Offline/degraded modes

* Minimum: each device continues to function if cloud is down (local cache)
* Recommended: optional local relay for in-venue continuity (phase later)

---

# 13) Technical architecture (implementation-friendly)

## 13.1 Suggested stack (web-first)

* Frontend: React + PWA (Next.js or Vite)
* Backend: Node/NestJS or FastAPI
* DB: Postgres
* Cache/queue: Redis (optional)
* Realtime: WebSockets/SSE per location
* Storage: S3-compatible for assets (menu images)

## 13.2 Domain events & idempotency

* All writes create a `domain_event`
* `idempotency_key` per client action to prevent duplicates
* Useful for offline replays later

## 13.3 Realtime updates

* Waiter inbox receives draft updates live
* KDS receives ticket updates live
* Guest receives status updates live

---

# 14) Testing strategy (built for LLM execution)

## 14.1 Global test gates

* **Playwright fails on any `console.error`**
* Screenshots + traces on failure
* API contract tests for every endpoint

## 14.2 Test types

### Unit tests

* draft state machine + locking
* version conflict handling
* ticket routing (station/course)
* pricing/tax calculations
* RBAC permission checks

### Integration tests

* guest draft submit/update → waiter sees updated
* waiter lock blocks guest edits
* confirm generates correct tickets (bar fired, food held)
* payment state transitions & reconciliation

### Playwright E2E (minimum suite list)

1. `guest_create_draft_submit_update.spec.ts`
2. `guest_update_blocked_when_in_review.spec.ts`
3. `waiter_inbox_filters_and_badges.spec.ts`
4. `waiter_edit_and_confirm_fire_drinks.spec.ts`
5. `expo_fire_mains_creates_kitchen_ticket.spec.ts`
6. `kds_station_filter_only_bar.spec.ts`
7. `reassign_table_before_confirm.spec.ts`
8. `pos_checkout_cash_and_print_receipt.spec.ts`
9. `pay_at_table_qr_flow_mocked.spec.ts` (mock provider initially)
10. `rbac_waiter_cannot_refund.spec.ts`

### Manual QA “human scripts”

* QR swapped between tables → waiter reassigns
* Rush: 15 drafts in 5 min → confirm without losing track
* Draft update race: guest updates while waiter is walking → waiter sees updated badge
* Kitchen pacing: confirm drinks, fire mains later, ensure correct station outputs
* Refund attempt: waiter blocked, manager allowed

---

# 15) Phased delivery plan (parallelizable)

## Phase 0 — Foundations (auth, tenancy, RBAC, core entities)

**DoD:** multi-tenant login, roles, location scoping, base entities.

## Phase 1 — Draft-first + waiter handheld + tables

**DoD:** guest draft app + waiter inbox + confirm → creates check.

## Phase 2 — Tickets + KDS + coursing (bar first)

**DoD:** confirm fires drinks to BAR KDS; later fire mains to KITCHEN.

## Phase 3 — POS checkout + printing + shifts

**DoD:** cash/external capture, receipts, shift close totals.

## Phase 4 — Pay at table QR

**DoD:** create payment intent, render QR, webhook closes check (mock then real).

## Phase 5 — Multi-warehouse simple stock

**DoD:** stock movements, transfers, low-stock alerts.

---

# 16) Multi-agent LLM execution plan (work division)

Below is the **exact agent decomposition** (each agent outputs artifacts that unblock others). This is optimized for multi-agent orchestration.

## Agent A — Product/UX Agent

**Outputs**

* Screen inventory + navigation map
* UX specs for each screen (guest, waiter, POS, KDS, admin)
* Copy text + empty/loading/error states
  **Dependencies:** none

## Agent B — Domain Modeling Agent

**Outputs**

* ERD + entity definitions
* State machines (Draft, Check, Ticket, Payment)
* Event definitions (domain events)
  **Dependencies:** Agent A partial (screen needs)

## Agent C — API Contract Agent

**Outputs**

* REST/GraphQL endpoints + payload schemas
* Idempotency strategy
* Realtime channels/events
  **Dependencies:** Agent B

## Agent D — Frontend App Agent (PWA)

**Outputs**

* UI routes/components scaffolds
* Local state strategy + caching
* Playwright selectors strategy (stable `data-testid`)
  **Dependencies:** Agent A + Agent C

## Agent E — Backend Services Agent

**Outputs**

* Service modules (drafts, orders, tickets, payments)
* RBAC middleware
* DB migrations
  **Dependencies:** Agent B + Agent C

## Agent F — Realtime & KDS Agent

**Outputs**

* WebSocket/SSE design
* KDS ticket views + station filters
* Expo actions (fire course, bump)
  **Dependencies:** Agent C

## Agent G — Printing/Hardware Agent

**Outputs**

* Printer abstraction interface
* Templates
* Optional local print bridge spec (install + auth)
  **Dependencies:** Agent C (print job endpoints)

## Agent H — Payments Agent

**Outputs**

* Cash/external capture flows
* QR payment integration plan (mock → real)
* Webhook handler + test harness
  **Dependencies:** Agent C

## Agent I — QA/Test Agent

**Outputs**

* Unit test plan mapped to modules
* Playwright suite implementation plan
* Manual QA scripts
* “console error gate” enforcement
  **Dependencies:** A/C/E/F/H

## Agent J — DevOps/Deployment Agent

**Outputs**

* Multi-tenant deployment model
* Environment config
* Observability (logs, tracing, error reporting)
  **Dependencies:** E

### Orchestration dependency graph (simple)

A → B → C → (D,E,F,G,H) → I → J

---

## 17) Ready-to-run task board (epics → stories)

If you’re orchestrating with an LLM, create work items like this:

### Epic: Draft-first ordering

* Story: Create Draft (guest)
* Story: Submit/Update Draft + versioning
* Story: Waiter inbox lists SUBMITTED/UPDATED
* Story: Lock draft on open (IN_REVIEW)
* Story: Confirm draft → create check + order snapshot
* Story: Reject draft with reason + rate limit

### Epic: Coursing & tickets

* Story: Station mapping on menu items
* Story: Confirm fires DRINKS to BAR
* Story: Expo fires MAINS to KITCHEN
* Story: KDS station filter, bump, ready

### Epic: POS & payments

* Story: Cash checkout + receipt
* Story: External terminal capture record
* Story: Shift close reconciliation

### Epic: Pay-at-table QR

* Story: Create payment intent
* Story: Render QR in guest app
* Story: Webhook marks paid + closes check

### Epic: Printing

* Story: Print job API + templates
* Story: Network printer config UI
* Story: Optional local print bridge

---

If you want, next message I can generate:

1. The **full screen-by-screen UX spec** (with components, states, and `data-testid` naming), and
2. The **API contract** (OpenAPI-style) + the **domain event list**,
   so you can feed it directly into your multi-agent dev setup.
