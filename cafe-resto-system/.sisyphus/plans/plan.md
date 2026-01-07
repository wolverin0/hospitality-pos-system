# Hospitality OS (Draft-first QR) - Implementation Plan

**Version:** 1.0  
**Date:** 2026-01-06  
**Status:** COMPLETE

---

## Executive Summary

Multi-tenant restaurant POS system with draft-first QR ordering, KDS, and comprehensive payment integration.

**Key Constraints:**
- Draft-first ordering (guest never creates kitchen tickets directly)
- Offline-first operations (devices function during cloud outages)
- Multi-tenant native architecture
- PWA web-first approach (no native apps in v1)

**Scope:** PRD v1 requirements (5 phases, 10-14 weeks)

---

## Technical Decisions

### Stack Selection

**Frontend:** Next.js 14+ (App Router) + PWA + Zustand + React Query + Socket.IO Client + Playwright
**Backend:** FastAPI (Python) + SQLModel + PostgreSQL + Redis + Alembic
**Infrastructure:** Docker + NGINX + Structlog + Prometheus
**Printing:** Go service (go-escpos) + ESC/POS templates
**Payments:** Mercado Pago (QR Attended + Terminal) + Cash

---

## Phase-by-Phase Implementation

### Phase 0: Foundations (Week 1-2)

**Stories:**
1. Project Setup (monorepo, Docker Compose, CI/CD)
2. Multi-Tenant Infrastructure (tenant model, RLS policies)
3. Authentication & RBAC (JWT, permissions, middleware)
4. Core Entities (location, table, user models)

**DoD:** Multi-tenant login works, tenant isolation enforced, RBAC blocks unauthorized access

---

### Phase 1: Draft-First + Waiter Handheld (Week 3-5)

**Stories:**
1. Guest Draft App (QR scan, menu, draft creation, call waiter)
2. Draft State Machine (OPEN, SUBMITTED, UPDATED, IN_REVIEW, CONFIRMED, REJECTED)
3. Waiter Handheld (drafts inbox, lock, edit, confirm, reject)
4. Confirm Workflow (create check + order + domain event)

**DoD:** Guest creates draft, waiter confirms, real-time updates work

---

### Phase 2: Tickets + KDS + Coursing (Week 6-8)

**Stories:**
1. Menu Station/Course Mapping (BAR, KITCHEN, DRINKS, MAINS)
2. Ticket Generation (confirm fires DRINKS, other courses staged)
3. KDS PWA (station filter, ticket queue, bump, ready)
4. Expo Mode (fire courses, reassign items, reprint)
5. Real-time Updates (WebSocket + Redis pub/sub)

**DoD:** KDS displays tickets, updates in real-time, Expo fires courses

---

### Phase 3: POS Checkout + Printing + Shifts (Week 9-10)

**Stories:**
1. POS PWA (walk-in orders, cart, checkout)
2. Payment Processing (cash, external terminal capture)
3. Receipt Printing (print service, templates, queue)
4. Shift Management (open/close, reconciliation, reports)
5. Print Bridge Service (Go + ESC/POS, printer discovery)

**DoD:** POS checkout works, receipts print, shift close reconciles cash

---

### Phase 4: Pay-at-Table QR (Week 11-12)

**Stories:**
1. Mercado Pago Integration (SDK, payment intent, QR generation)
2. Pay-at-Table Flow (guest sees pay button, creates intent, renders QR)
3. Webhook Security (signature verification, idempotency, retry)
4. Error Handling (payment failed, expired, fallback polling)

**DoD:** Guest pays at table, webhook confirms, check closes

---

### Phase 5: Multi-Warehouse Simple Stock (Week 13-14)

**Stories:**
1. Warehouse Setup (location-scoped, stock items)
2. Stock Movements (RECEIVE, SELL, TRANSFER, ADJUSTMENT)
3. Stock Management (low-stock alerts, reports, transfers)
4. Integration (link sold items to stock, admin UI)

**DoD:** Warehouses manage stock, movements tracked, alerts generated

---

## Task Dependencies

Critical Path:
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5

Parallelizable:
- Frontend ⊥ Backend setup
- Guest PWA ⊥ Waiter PWA
- KDS ⊥ Expo UI
- POS ⊥ Print bridge
- Payment integration ⊥ Webhook security

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Multi-tenant performance | Connection pooling, tenant_id indexes, monitoring |
| WebSocket reliability | Redis pub/sub, reconnection logic, polling fallback |
| ESC/POS printer issues | Multiple printer testing, retry logic, Printercow compatibility |
| Payment webhook delays | Exponential backoff, fallback polling, idempotency |
| Offline sync conflicts | Optimistic UI, server wins, audit trail |

---

## Success Criteria

- ✅ All 10 Playwright E2E tests pass (from PRD)
- ✅ Zero console.errors in E2E tests
- ✅ Multi-tenant isolation verified (100+ concurrent tenants)
- ✅ Offline mode works (cloud outage → device continuity)
- ✅ Real-time updates <300ms for KDS
- ✅ Waiter inbox loads <1s for 200+ active tables
- ✅ Confirm fires DRINKS to BAR within 500ms

---

## Research References

**PWA POS:**
- OrderWorder (Next.js POS with QR + KDS)
- nextjs-restaurant-pwa (PWA patterns)

**Multi-Tenant:**
- moofoo/nestjs-multi-tenant-example (RLS pattern)
- Multi-Tenant FastAPI Architecture (Medium article)

**Printing:**
- Printrz (Electron bridge)
- QZ Tray (WebSocket bridge)
- Printercow (hardware bridge)
- go-escpos (ESC/POS Go library)
- python-escpos (ESC/POS Python library)

**Payments:**
- Mercado Pago SDK (Python/Node.js)
- Mercado Pago QR Integration Docs
- Payment webhook patterns (Stripe, Adyen examples)

**Real-time:**
- Socket.IO Multi-Instance with Redis
- FastAPI WebSocket documentation
- SSE vs WebSocket patterns

---

**Plan Status:** COMPLETE  
**Ready for Implementation:** YES (run `/start-work`)

