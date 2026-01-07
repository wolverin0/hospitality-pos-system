"""
Integration tests for guest → waiter → confirm flow
Tests the complete flow from guest creating a draft to waiter confirming it.
"""

import pytest
from httpx import AsyncClient
from datetime import datetime
import uuid

from app.models.draft_order import DraftOrder, DraftStatus
from app.models.table_session import TableSession, TableSessionStatus
from app.models.draft_line_item import DraftLineItem
from app.core.database import get_session
from app.main import app


@pytest.fixture
async def client():
    """Create test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_tenant_id(client: AsyncClient):
    """Create or get test tenant"""
    # Create tenant
    response = await client.post(
        "/api/v1/tenants/",
        json={
            "name": "Test Restaurant",
            "slug": "test-restaurant",
            "owner_email": "owner@test.com"
        }
    )
    tenant_data = response.json()
    return uuid.UUID(tenant_data["id"])


@pytest.fixture
async def test_location_id(client: AsyncClient, test_tenant_id: uuid.UUID):
    """Create test location"""
    response = await client.post(
        "/api/v1/locations/",
        json={
            "tenant_id": str(test_tenant_id),
            "name": "Main Location",
            "address": "123 Main St",
            "city": "Test City",
            "state": "TS",
            "zip_code": "12345"
        }
    )
    location_data = response.json()
    return uuid.UUID(location_data["id"])


@pytest.fixture
async def test_table_id(client: AsyncClient, test_tenant_id: uuid.UUID, test_location_id: uuid.UUID):
    """Create test table"""
    response = await client.post(
        "/api/v1/tables/",
        json={
            "tenant_id": str(test_tenant_id),
            "location_id": str(test_location_id),
            "name": "A1",
            "capacity": 4
        }
    )
    table_data = response.json()
    return uuid.UUID(table_data["id"])


@pytest.fixture
async def test_menu_category_id(client: AsyncClient, test_tenant_id: uuid.UUID, test_location_id: uuid.UUID):
    """Create test menu category"""
    response = await client.post(
        "/api/v1/menu-categories/",
        json={
            "tenant_id": str(test_tenant_id),
            "location_id": str(test_location_id),
            "name": "Appetizers"
        }
    )
    category_data = response.json()
    return uuid.UUID(category_data["id"])


@pytest.fixture
async def test_menu_item_id(client: AsyncClient, test_tenant_id: uuid.UUID, test_location_id: uuid.UUID, test_menu_category_id: uuid.UUID):
    """Create test menu item"""
    response = await client.post(
        "/api/v1/menu-items/",
        json={
            "tenant_id": str(test_tenant_id),
            "location_id": str(test_location_id),
            "category_id": str(test_menu_category_id),
            "name": "Nachos",
            "description": "Crispy tortilla chips with cheese",
            "price": 12.99
        }
    )
    item_data = response.json()
    return uuid.UUID(item_data["id"])


@pytest.fixture
async def test_user_id(client: AsyncClient, test_tenant_id: uuid.UUID):
    """Create test user (waiter)"""
    response = await client.post(
        "/api/v1/users/",
        json={
            "tenant_id": str(test_tenant_id),
            "email": "waiter@test.com",
            "password": "password123",
            "first_name": "John",
            "last_name": "Waiter",
            "role": "waiter"
        }
    )
    user_data = response.json()
    return uuid.UUID(user_data["id"])


@pytest.fixture
async def auth_headers(client: AsyncClient, test_user_id: uuid.UUID):
    """Get authentication headers for test user"""
    # Login to get token
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "waiter@test.com",
            "password": "password123"
        }
    )
    token_data = response.json()
    access_token = token_data["access_token"]

    return {
        "Authorization": f"Bearer {access_token}",
        "X-Tenant-ID": "test-restaurant"
    }


class TestGuestToWaiterToConfirmFlow:
    """Integration tests for complete guest→waiter→confirm flow"""

    async def test_guest_creates_draft(
        self,
        client: AsyncClient,
        test_table_id: uuid.UUID,
        test_menu_item_id: uuid.UUID
    ):
        """Test guest creates a draft"""
        # Create table session (simulating QR scan)
        session_response = await client.post(
            "/api/v1/table-sessions/",
            json={
                "table_id": str(test_table_id),
                "guest_count": 2
            },
            headers={"X-Tenant-ID": "test-restaurant"}
        )
        session_data = session_response.json()
        table_session_id = uuid.UUID(session_data["id"])

        # Create draft
        draft_response = await client.post(
            "/api/v1/drafts/",
            json={
                "table_session_id": str(table_session_id),
                "line_items": [
                    {
                        "menu_item_id": str(test_menu_item_id),
                        "name": "Nachos",
                        "quantity": 2,
                        "price_at_order": 12.99,
                        "sort_order": 1
                    }
                ],
                "special_requests": "Extra cheese, please"
            },
            headers={"X-Tenant-ID": "test-restaurant"}
        )

        assert draft_response.status_code == 200
        draft_data = draft_response.json()
        assert draft_data["status"] == "draft"
        assert draft_data["table_session_id"] == str(table_session_id)

        # Submit draft for review
        submit_response = await client.post(
            f"/api/v1/drafts/{draft_data['id']}/submit",
            headers={"X-Tenant-ID": "test-restaurant"}
        )

        assert submit_response.status_code == 200
        submitted_draft = submit_response.json()
        assert submitted_draft["status"] == "pending"

        return uuid.UUID(draft_data["id"])

    async def test_waiter_sees_draft_in_inbox(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_draft_id: uuid.UUID
    ):
        """Test waiter sees draft in inbox"""
        # List pending drafts
        response = await client.get(
            "/api/v1/drafts/?status=pending",
            headers=auth_headers
        )

        assert response.status_code == 200
        drafts = response.json()
        assert len(drafts) >= 1

        # Find our draft
        found = False
        for draft in drafts:
            if draft["id"] == str(test_draft_id):
                found = True
                assert draft["status"] == "pending"
                break

        assert found is True

    async def test_waiter_acquires_lock(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_draft_id: uuid.UUID
    ):
        """Test waiter acquires lock on draft"""
        # Acquire lock
        response = await client.patch(
            f"/api/v1/drafts/{test_draft_id}/acquire",
            headers=auth_headers
        )

        assert response.status_code == 200
        lock_data = response.json()
        assert lock_data["message"] == "Lock acquired"
        assert lock_data["draft_id"] == str(test_draft_id)
        assert lock_data["locked_at"] is not None

        # Verify draft is locked
        draft_response = await client.get(
            f"/api/v1/drafts/{test_draft_id}",
            headers=auth_headers
        )
        draft_data = draft_response.json()
        assert draft_data["locked_by"] is not None

    async def test_lock_conflict_with_another_waiter(
        self,
        client: AsyncClient,
        test_draft_id: uuid.UUID,
        test_user_id: uuid.UUID
    ):
        """Test another waiter cannot acquire locked draft"""
        # Create second waiter user
        second_user_response = await client.post(
            "/api/v1/users/",
            json={
                "tenant_id": "test-restaurant",
                "email": "waiter2@test.com",
                "password": "password123",
                "first_name": "Jane",
                "last_name": "Waiter",
                "role": "waiter"
            }
        )
        second_user_data = second_user_response.json()
        second_user_id = uuid.UUID(second_user_data["id"])

        # Login as second waiter
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "waiter2@test.com",
                "password": "password123"
            }
        )
        token_data = login_response.json()
        second_auth_headers = {
            "Authorization": f"Bearer {token_data['access_token']}",
            "X-Tenant-ID": "test-restaurant"
        }

        # Try to acquire lock (should fail)
        response = await client.patch(
            f"/api/v1/drafts/{test_draft_id}/acquire",
            headers=second_auth_headers
        )

        assert response.status_code == 409  # Conflict
        error_data = response.json()
        assert "already locked by another user" in error_data["detail"]

    async def test_waiter_confirms_draft(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_draft_id: uuid.UUID
    ):
        """Test waiter confirms draft and creates order"""
        # Confirm draft
        response = await client.patch(
            f"/api/v1/drafts/{test_draft_id}/confirm",
            headers=auth_headers
        )

        assert response.status_code == 200
        confirm_data = response.json()
        assert confirm_data["message"] == "Draft confirmed"
        assert confirm_data["draft_id"] == str(test_draft_id)
        assert confirm_data["order_id"] is not None

        # Verify draft status changed to confirmed
        draft_response = await client.get(
            f"/api/v1/drafts/{test_draft_id}",
            headers=auth_headers
        )
        draft_data = draft_response.json()
        assert draft_data["status"] == "confirmed"
        assert draft_data["order_id"] == confirm_data["order_id"]
        assert draft_data["locked_by"] is None  # Lock should be released

    async def test_version_conflict_on_update(
        self,
        client: AsyncClient,
        test_draft_id: uuid.UUID
    ):
        """Test version conflict when updating draft"""
        # Get draft with version 1
        draft_response = await client.get(
            f"/api/v1/drafts/{test_draft_id}",
            headers={"X-Tenant-ID": "test-restaurant"}
        )
        draft_data = draft_response.json()
        version = draft_data["version"]

        # Try to update with wrong version (simulating concurrent update)
        update_response = await client.patch(
            f"/api/v1/drafts/{test_draft_id}",
            json={
                "version": version - 1,  # Wrong version
                "special_requests": "Updated request"
            },
            headers={"X-Tenant-ID": "test-restaurant"}
        )

        assert update_response.status_code == 409  # Conflict
        error_data = update_response.json()
        assert "version" in error_data["detail"]

    async def test_complete_flow(
        self,
        client: AsyncClient,
        test_table_id: uuid.UUID,
        test_menu_item_id: uuid.UUID,
        auth_headers: dict
    ):
        """Test complete flow from draft creation to confirmation"""
        # 1. Guest creates table session and draft
        session_response = await client.post(
            "/api/v1/table-sessions/",
            json={
                "table_id": str(test_table_id),
                "guest_count": 2
            },
            headers={"X-Tenant-ID": "test-restaurant"}
        )
        table_session_id = uuid.UUID(session_response.json()["id"])

        draft_response = await client.post(
            "/api/v1/drafts/",
            json={
                "table_session_id": str(table_session_id),
                "line_items": [
                    {
                        "menu_item_id": str(test_menu_item_id),
                        "name": "Nachos",
                        "quantity": 2,
                        "price_at_order": 12.99,
                        "sort_order": 1
                    }
                ]
            },
            headers={"X-Tenant-ID": "test-restaurant"}
        )
        draft_id = uuid.UUID(draft_response.json()["id"])

        # 2. Guest submits draft
        await client.post(
            f"/api/v1/drafts/{draft_id}/submit",
            headers={"X-Tenant-ID": "test-restaurant"}
        )

        # 3. Waiter sees draft in inbox
        inbox_response = await client.get(
            "/api/v1/drafts/?status=pending",
            headers=auth_headers
        )
        drafts = inbox_response.json()
        assert any(d["id"] == str(draft_id) for d in drafts)

        # 4. Waiter acquires lock
        await client.patch(
            f"/api/v1/drafts/{draft_id}/acquire",
            headers=auth_headers
        )

        # 5. Waiter confirms draft
        confirm_response = await client.patch(
            f"/api/v1/drafts/{draft_id}/confirm",
            headers=auth_headers
        )

        # 6. Verify order created
        assert confirm_response.status_code == 200
        confirm_data = confirm_response.json()
        assert confirm_data["order_id"] is not None
