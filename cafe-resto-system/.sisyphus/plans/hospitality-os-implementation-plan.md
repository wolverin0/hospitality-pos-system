# Hospitality OS (Draft-first QR) - Implementation Plan

**Version:** 1.0  
**Date:** 2026-01-06  
**Planner Mode:** Ultrawork (Planning Only)  
**Status:** Ready for Review

---

## Executive Summary

This implementation plan addresses the development of a multi-tenant, multi-location restaurant POS system with draft-first QR ordering, KDS, and comprehensive payment integration. The plan is based on comprehensive research of production systems, architectural patterns, and real-world implementations.

**Key Constraints:**
- **Draft-first ordering** (guest never creates kitchen tickets directly)
- **Offline-first operations** (devices must function during cloud outages)
- **Multi-tenant native architecture** (tenants → locations → registers/stations/tables/warehouses)
- **PWA web-first approach** (no native apps in v1)

**Scope:** PRD v1 requirements (5 phases, ~10-12 week timeline with multi-agent execution)

---

## Research Findings Summary

### 1. Current State
- **Ground zero** - Only PRD.md exists
- **Deprecated implementation** exists (Turborepo, NestJS, Next.js, Prisma/Postgres) - available for reference
- **No code, no infrastructure** - Fresh start required

### 2. Recommended Tech Stack (Based on Production Evidence)

**Frontend:**
- **Framework:** Next.js 14+ (App Router) with PWA
- **State Management:** Zustand for global state + React Query for server state
- **Real-time:** Socket.IO Client (WebSocket) for kitchen/waiter coordination
- **PWA:** @ducanh2912/next-pwa with Workbox
- **UI Components:** Radix UI + Tailwind CSS
- **Testing:** Playwright (required for E2E with console.error gate)

**Backend:**
- **Framework:** FastAPI (Python) - Chosen for:
  - Async performance (comparable to Go/Node.js)
  - Type safety (Pydantic models)
  - Built-in API documentation (OpenAPI)
  - Strong WebSocket support
  - Multi-tenant patterns well-documented
- **ORM:** SQLModel (SQLAlchemy + Pydantic hybrid) - Best of both worlds
- **Database:** PostgreSQL 16+
- **Caching/Queue:** Redis (for real-time pub/sub, job queues)
- **Real-time:** FastAPI WebSocket + Redis pub/sub for multi-instance
- **Migration:** Alembic

**Infrastructure:**
- **Deployment:** Docker + Docker Compose (local), Kubernetes (production)
- **Reverse Proxy:** NGINX (multi-tenant routing)
- **Observability:** Structlog + Prometheus + Grafana

### 3. Print Bridge Architecture (Recommended)

**Primary Option: Go-based Native Service**
- **Library:** go-escpos (mect/kenshaw forks)
- **Implementation:**
  - Go microservice handles ESC/POS encoding
  - REST API for job submission
  - Printer discovery (network scan + mDNS)
  - Job queue with retry logic
  - Status monitoring

**Secondary Option (Hardware): Printercow**
- Raspberry Pi Zero W2 + USB thermal printer
- REST API for remote printing
- Best for multi-location deployments

**Template System:**
- Custom JSON-based template engine (inspired by escpos-template)
- Receipt templates (customer + merchant copy)
- Kitchen/bar ticket templates

### 4. Payment Integration (Argentina Focus)

**Primary: Mercado Pago**
- **QR Attended Model:** Fixed QR codes at tables
- **Terminal Integration:** Point terminal for card capture
- **Flow:**
  1. Table QR scan → opens guest app
  2. Guest creates order (draft)
  3. Waiter confirms → creates check
  4. POS creates payment intent (QR or terminal)
  5. Customer pays → webhook confirms
  6. Check closes → receipt prints

**Implementation Pattern:**
- Idempotency keys on all payment mutations
- HMAC signature verification on webhooks
- Exponential backoff for retry logic
- Multi-tenant payment intent isolation (tenant_id on all tables)
- Offline recording + reconciliation

**Secondary: Cash**
- Built-in cash management
- Shift close reconciliation (expected vs actual)
- Reason codes for discrepancies

---

## Technical Decisions & Justification

### Decision 1: FastAPI vs NestJS vs Go

**Selected: FastAPI (Python)**

**Justification:**
1. **Multi-tenant patterns well-documented** in Python community (Medium articles, OSS examples)
2. **Async performance** rivals Go/Node.js for I/O-bound workloads (order management, websockets)
3. **Type safety** with Pydantic + SQLModel provides compile-time validation
4. **Development speed** - Python's expressiveness accelerates LLM-driven multi-agent workflows
5. **Real-time support** - Native WebSocket + Redis pub/sub is straightforward
6. **Library ecosystem** - Mature payment integrations (mercadopago-sdk-python, escpos adapters)

**Trade-offs:**
- Slightly slower raw performance than Go (acceptable for I/O-bound POS workload)
- Not as opinionated as NestJS (need to enforce architectural patterns)

### Decision 2: PostgreSQL Row-Level Security (RLS) vs Schema-per-Tenant

**Selected: Shared Database + RLS**

**Justification:**
1. **Cost-effective** - Single database instance reduces hosting costs
2. **Easier migrations** - Single schema to version and upgrade
3. **Good enough isolation** - RLS enforced at DB level prevents cross-tenant data access
4. **Scalable to 100s of tenants** - Performance studies show acceptable degradation

**Implementation:**
```sql
-- Enable RLS on sensitive tables
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

-- Tenant isolation policy
CREATE POLICY tenant_isolation ON orders
FOR ALL
USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- Set tenant context per request
SET app.current_tenant = 'tenant-uuid';
```

### Decision 3: WebSocket vs SSE for Real-time

**Selected: Hybrid Approach**
- **WebSocket (Socket.IO):** Kitchen → Waiter → Expo coordination (bidirectional, low latency)
- **SSE:** Guest → Status updates (server-to-client only, simpler)

**Justification:**
- Kitchen/waiter coordination requires complex bidirectional messaging (fire course, bump, reassign)
- Guest status updates are simple notifications (order ready, paid)
- Hybrid approach optimizes complexity per use case

### Decision 4: Offline Strategy

**Selected: Service Worker + IndexedDB + Background Sync**

**Implementation:**
1. **Service Worker:** Cache app shell (offline-first load)
2. **IndexedDB:** Store local orders, drafts, menu data
3. **Background Sync:** Queue mutations for when online
4. **Optimistic UI:** Show updates immediately, sync in background
5. **Conflict Resolution:** Server wins with audit trail

**Trade-offs:**
- Browser storage limits (~50MB per origin) - acceptable for POS data
- No LAN relay in v1 (cloud outage → device-only continuity)

---

## Architecture Overview

### High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Guest PWA│  │ Waiter   │  │ POS PWA  │  │ KDS PWA  │  │
│  │ (Mobile) │  │ (Tablet) │  │ (Desktop)│  │ (Large)  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
│       │              │              │              │           │
└───────┼──────────────┼──────────────┼──────────────┼─────────┘
        │              │              │              │
        │              │              │              │
┌───────┴──────────────┴──────────────┴──────────────┴─────────┐
│                    API Gateway (NGINX)                         │
│              Tenant routing + SSL termination                   │
└───────┬──────────────┬──────────────┬──────────────┬─────────┘
        │              │              │              │
┌───────┴──────────────┴──────────────┴──────────────┴─────────┐
│                  Backend Services (FastAPI)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ Auth     │  │ Orders   │  │ Payments │  │ Menu     │      │
│  │ Service  │  │ Service  │  │ Service  │  │ Service  │      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘      │
│       │              │              │              │              │
│  ┌────┴─────┐  ┌────┴─────┐  ┌────┴─────┐  ┌────┴─────┐      │
│  │ WebSocket│  │ RBAC MW  │  │ Events   │  │ Tenant   │      │
│  │ Gateway  │  │        
