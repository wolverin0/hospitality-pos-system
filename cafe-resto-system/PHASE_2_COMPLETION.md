# Phase 2: Kitchen Display System (KDS) - COMPLETED

## Overview
Phase 2 implemented a complete Kitchen Display System (KDS) with ticket management, WebSocket real-time updates, and a responsive PWA for kitchen staff.

## Deliverables

### 2.0: Menu Station & Course Models ✅
**Files Created:**
- `backend/app/models/menu_station.py` - Menu station model with station types
- `backend/app/models/kitchen_course.py` - Kitchen course model with course types

**Features:**
- Station Types: BAR, KITCHEN, EXPO, GRILL, FRYER, SALAD, DESSERT, PREP, SUSHI, PIZZA, CUSTOM
- Course Types: DRINKS, APPETIZERS, SOUPS, SALADS, MAINS, DESSERT, COFFEE, CUSTOM
- Each station supports 0..n printers
- Auto-fire configuration per course
- Filter rules via item types and category IDs
- Display configuration (color, icon, display order)

### 2.1: Ticket Model ✅
**File Created:**
- `backend/app/models/ticket.py` - Ticket model

**Features:**
- Statuses: NEW, PENDING, PREPARING, READY, IN_PROGRESS, COMPLETED, CANCELLED, VOIDED
- Course information (number, name)
- Priority (is_rush, priority_level)
- Expo mode (is_held, held_reason, held_at)
- Timing fields (prep_started_at, ready_at, completed_at, fired_at)
- Display information (table_number, server_name)
- Special instructions
- Printing (print_count, last_printed_at)
- Void tracking (voided_at, voided_by, voided_reason)
- Optimistic concurrency (version field)
- Proper indexes for performance

### 2.2: Ticket Line Item Model ✅
**File Created:**
- `backend/app/models/ticket_line_item.py` - Ticket line item model

**Features:**
- Fired Status: PENDING, FIRED, HELD, VOIDED, COMPLETED
- Snapshot data (name, description, quantity, price_at_order, line_total)
- Course assignment (number, name)
- Firing tracking (fired_at, held_at, held_reason, fired_status)
- Preparation status (preparation_status, preparation_started_at, preparation_completed_at)
- Special instructions
- Modifiers (JSON field for flexibility)
- Sort order for display
- Parent/child relationships for modifications
- Optimistic concurrency (version field)

### 2.3: KDS PWA ✅
**Location:**
- `apps/kds/` - React TypeScript PWA

**Features:**
- Station filtering (BAR, KITCHEN, GRILL, FRYER, SALAD, DESSERT, PREP, SUSHI, PIZZA, CUSTOM)
- Ticket queue display with sorting by priority and time
- Ticket cards with color-coded statuses
- Ticket details view with line items and modifiers
- Action buttons: bump, hold, fire, void
- Timer display with color warnings
- WebSocket hooks for real-time updates
- Dark mode optimized for kitchen environment
- PWA capabilities (manifest, offline support)
- Responsive design

### 2.4: Ticket Generation API ✅
**File Created:**
- `backend/app/api/tickets.py` - Ticket management endpoints

**Endpoints:**
- `POST /api/v1/tickets/generate` - Generate tickets from confirmed draft orders
- `GET /api/v1/tickets/` - List tickets with filters (station, status, course, table)
- `GET /api/v1/tickets/{id}` - Get ticket details with line items
- `DELETE /api/v1/tickets/{id}` - Delete ticket (admin only)

**Logic:**
- Group draft line items by (station_id, course_id)
- Create one ticket per station per course
- Auto-fire courses with `auto_fire_on_confirm=True` (typically DRINKS)
- Non-auto-fire courses start as NEW until Expo fires them
- Capture all draft line item data as snapshots
- Sort tickets by: rush (descending), course_number (ascending), created_at (ascending)
- Don't show completed tickets older than 24 hours

### 2.5: Ticket Status Update APIs ✅
**Endpoints:**
- `PATCH /api/v1/tickets/{id}/bump` - Bump to COMPLETED (move to top of queue)
- `PATCH /api/v1/tickets/{id}/status` - Manual status update
- `DELETE /api/v1/tickets/line-items/{id}` - Void line item

**Logic:**
- Set appropriate timestamps based on status:
  - PREPARING → prep_started_at
  - READY → ready_at
  - COMPLETED → completed_at
- All operations use optimistic concurrency with version field
- Permission checks: void requires admin/manager role

### 2.6: Expo Mode APIs ✅
**Endpoints:**
- `PATCH /api/v1/tickets/{id}/hold` - Hold ticket (prevents firing)
- `PATCH /api/v1/tickets/{id}/fire` - Fire held ticket to kitchen
- `PATCH /api/v1/tickets/{id}/void` - Void ticket (admin/manager only)
- `POST /api/v1/tickets/{id}/reassign` - Reassign to different station
- `POST /api/v1/tickets/{id}/reprint` - Reprint ticket

**Logic:**
- Hold requires reason parameter
- Fire only works on held tickets
- Void requires reason and admin/manager role
- Reassign validates new station exists
- Reprint increments print_count
- All update line items appropriately (HELD/FIRED/VOIDED status)
- All use optimistic concurrency with version field
- Permission checks for void/reassign

### 2.7: WebSocket for Ticket Updates ✅
**Files Modified/Created:**
- `backend/app/core/events.py` - Added ticket event types
- `backend/app/core/websocket_manager.py` - Added station connections and ticket broadcast methods
- `backend/app/api/websockets.py` - WebSocket endpoints

**WebSocket Endpoints:**
- `WS /api/v1/ws/station/{station_id}` - KDS station WebSocket
- `WS /api/v1/ws/user/{user_id}` - User WebSocket
- `WS /api/v1/ws/table/{table_session_id}` - Table session WebSocket
- `GET /api/v1/ws/connections` - Get connection counts

**Event Types:**
- `TicketCreated` - When ticket generated
- `TicketUpdated` - When status changes
- `TicketBumped` - When bumped to COMPLETED
- `TicketHeld` - When held by Expo
- `TicketFired` - When held ticket fired
- `TicketVoided` - When ticket voided

**Logic:**
- Station filtering: Each KDS screen receives only its station's tickets
- Connection management: Track active station connections
- Event broadcasting: Send events to specific station's connected clients
- Validation: Validate station exists and is active, user belongs to tenant, table belongs to tenant

## Testing

### Phase 2.8: Unit Tests ✅
**File Created:**
- `backend/tests/test_tickets.py` - 13 unit tests

**Coverage:**
- Ticket creation from draft orders with auto-fire logic
- Status transitions (NEW → PENDING → PREPARING → READY → COMPLETED)
- Bump operation (move to COMPLETED, top of queue)
- Hold/fire operations (Expo mode)
- Void operation (admin/manager only)
- Course assignment logic (items go to correct station/course)
- Auto-fire vs Expo fire logic
- Optimistic concurrency (version field)
- Reassign operation (Expo mode)
- Reprint operation
- Permission checks

### Phase 2.9: Integration Tests ✅
**Files Created:**
- `backend/tests/test_ticket_integration.py` - 6 integration tests
- `backend/tests/test_websocket.py` - 12 WebSocket tests

**Coverage:**
- Complete ticket lifecycle from draft to completion
- Station routing (bar vs kitchen)
- Multiple items per station/course
- Auto-fire vs manual fire lifecycle differences
- Expo hold and fire workflow
- Ticket void workflow
- Priority sorting (rush first, then by time)
- WebSocket connection management
- All ticket events (created, updated, bumped, held, fired, voided)
- Station-specific event isolation
- Multiple clients per station
- Connection state management

### Phase 2.10: E2E Tests ✅
**File Created:**
- `apps/kds/tests/e2e/KDS.spec.ts` - 25+ E2E tests with Playwright

**Coverage:**
- Page load and layout
- Station filtering
- Ticket queue display
- Ticket actions (bump, hold, void, fire)
- Ticket details and line items
- Status bar counts
- Connection status indicators (ONLINE/OFFLINE)
- PWA features (manifest, offline support)
- Accessibility checks
- Performance tests (load time < 3s)

## Code Quality

### Issues Fixed:
1. ✅ Added missing `locked_by_user` relationship to `DraftOrder`
2. ✅ Fixed `DraftLineItem` self-referential relationships (removed circular reference)
3. ✅ Fixed `TicketLineItem` self-referential relationships (removed circular reference)
4. ✅ Fixed `tickets.py` to use `confirmed_by_user` instead of `locked_by_user`
5. ✅ Removed duplicate code from `tickets.py` (lines 1011-1986)
6. ✅ Updated test infrastructure (`conftest.py`) for SQLite in-memory database

### Test Coverage:
- **Backend**: 18 test files (8 existing + 10 new)
- **Frontend**: 2 E2E test files
- **Total Test Cases**: 55+

## Database

### Migrations Applied:
- `2026_01_07_9dfb6218bc5d_add_menu_station_and_kitchen_course.py` - Initial stations/courses
- `2026_01_07_14a939f9d226_add_ticket_and_ticket_line_item.py` - Ticket models
- `2026_01_07_e40349bce913_add_version_field_to_tickets.py` - Optimistic concurrency

## API Endpoints Summary

### Total New Endpoints: 13
1. `POST /api/v1/tickets/generate` - Generate tickets
2. `PATCH /api/v1/tickets/{id}/bump` - Bump ticket
3. `PATCH /api/v1/tickets/{id}/hold` - Hold ticket
4. `PATCH /api/v1/tickets/{id}/fire` - Fire ticket
5. `PATCH /api/v1/tickets/{id}/void` - Void ticket
6. `PATCH /api/v1/tickets/{id}/status` - Update status
7. `DELETE /api/v1/tickets/line-items/{id}` - Void line item
8. `POST /api/v1/tickets/{id}/reassign` - Reassign ticket
9. `POST /api/v1/tickets/{id}/reprint` - Reprint ticket
10. `GET /api/v1/tickets/` - List tickets
11. `GET /api/v1/tickets/{id}` - Get ticket details
12. `DELETE /api/v1/tickets/{id}` - Delete ticket
13. `GET /api/v1/menu-stations/` - List menu stations
14. `GET /api/v1/kitchen-courses/` - List kitchen courses
15. `WS /api/v1/ws/station/{station_id}` - Station WebSocket
16. `WS /api/v1/ws/user/{user_id}` - User WebSocket
17. `WS /api/v1/ws/table/{table_session_id}` - Table WebSocket
18. `GET /api/v1/ws/connections` - Connection counts

## Documentation

### API Usage

#### Generating Tickets from Draft Orders
```bash
curl -X POST http://localhost:8000/api/v1/tickets/generate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "draft_order_id": "<uuid>"
  }'
```

#### Bumping Ticket
```bash
curl -X PATCH http://localhost:8000/api/v1/tickets/{ticket_id}/bump \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "version": 1
  }'
```

#### Holding Ticket
```bash
curl -X PATCH http://localhost:8000/api/v1/tickets/{ticket_id}/hold \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "version": 1,
    "reason": "Waiting for special ingredient"
  }'
```

#### Firing Held Ticket
```bash
curl -X PATCH http://localhost:8000/api/v1/tickets/{ticket_id}/fire \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "version": 2
  }'
```

#### Voiding Ticket
```bash
curl -X PATCH http://localhost:8000/api/v1/tickets/{ticket_id}/void \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "version": 3,
    "reason": "Customer cancelled"
  }'
```

#### Reassigning Ticket
```bash
curl -X POST http://localhost:8000/api/v1/tickets/{ticket_id}/reassign \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "version": 4,
    "new_station_id": "<station_uuid>",
    "reason": "Kitchen overloaded"
  }'
```

### WebSocket Connection

#### Station WebSocket (KDS)
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/station/<station_id>?token=<jwt_token>');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch (data.type) {
    case 'ticket_created':
      // Update ticket queue
      addTicketToQueue(data.ticket);
      break;
    case 'ticket_updated':
      // Update existing ticket
      updateTicketInQueue(data.ticket);
      break;
    case 'ticket_bumped':
      // Move to top of completed queue
      bumpTicketToTop(data.ticket_id);
      break;
    case 'ticket_held':
      // Show held indicator
      showHeldIndicator(data.ticket_id, data.reason);
      break;
    case 'ticket_fired':
      // Update to preparing
      updateTicketStatus(data.ticket_id, 'preparing');
      break;
    case 'ticket_voided':
      // Remove from queue
      removeTicket(data.ticket_id);
      break;
  }
};
```

## Testing

### Running Unit Tests
```bash
# From backend directory
pytest tests/test_tickets.py -v

# Run specific test
pytest tests/test_tickets.py::test_ticket_creation_from_draft_order -v

# With coverage
pytest --cov=app tests/test_tickets.py --cov-report=html
```

### Running Integration Tests
```bash
pytest tests/test_ticket_integration.py -v
pytest tests/test_websocket.py -v
```

### Running E2E Tests
```bash
# From kds directory
npm test

# Or run specific test suite
npx playwright test KDS.spec.ts

# Run tests with UI
npx playwright test KDS.spec.ts --ui

# Run tests in headed mode (see browser)
npx playwright test KDS.spec.ts --headed
```

## Notes

### Test Infrastructure
- Unit tests use SQLite in-memory for speed and simplicity
- Integration tests also use SQLite
- Production uses PostgreSQL
- Tests document expected behavior and can serve as specification

### WebSocket Events
All WebSocket events are defined in `app/core/events.py`:
- `TicketCreated` - Emitted when ticket generated
- `TicketUpdated` - Emitted when status changes
- `TicketBumped` - Emitted when bumped to COMPLETED
- `TicketHeld` - Emitted when held by Expo
- `TicketFired` - Emitted when held ticket fired
- `TicketVoided` - Emitted when ticket voided

### Model Relationships
All models properly configured with relationships:
- `DraftOrder` → `locked_by_user`, `confirmed_by_user`, `rejected_by_user`
- `Ticket` → `draft_order`, `table_session`, `station`, `line_items`
- `TicketLineItem` → `ticket`, `menu_item`
- `MenuItem` → `station`, `course`
- `MenuStation` → Has 0..n printers
- `KitchenCourse` → Has auto_fire_on_confirm flag

### Optimistic Concurrency
All ticket and ticket line item operations require:
- `version` field in request body
- Version mismatch returns HTTP 409 Conflict
- Version increments on each update

## Next Steps

Phase 3 will implement the POS system:
- Order model
- Payment model
- POS PWA
- Order creation API
- Cart management APIs
- Payment processing (cash, card, external terminal)
- Receipt model and printing
- Shift model and management
- WebSocket for order/payment updates

## Completion Status

✅ **Phase 2 Complete** - All requirements met
- All models created and migrated
- All API endpoints implemented
- WebSocket infrastructure complete
- KDS PWA functional
- Comprehensive test coverage
- Code quality issues resolved
- Documentation complete
