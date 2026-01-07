"""
E2E tests for full guest workflow
Tests guest scans QR, browses menu, adds items, submits draft, receives confirmation.
"""

import pytest
from playwright.async_api import async_playwright, Page, Browser
from datetime import datetime
import uuid


@pytest.fixture
async def browser():
    """Create Playwright browser instance"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.fixture
async def page(browser: Browser):
    """Create Playwright page"""
    page = await browser.new_page()
    yield page
    await page.close()


class TestGuestWorkflowE2E:
    """E2E tests for complete guest workflow"""

    async def test_qr_scan_creates_session(self, page: Page):
        """Test guest scans QR code and table session is created"""
        # Navigate to guest app
        await page.goto("http://localhost:3000")

        # Wait for QR scanner to be visible
        await page.wait_for_selector("[data-testid='qr-scanner']")

        # Simulate QR scan with test data
        await page.evaluate("""
            () => {
                const testData = {
                    table_id: '123e4567-e89b-12d3-a456-426614174000',
                    location_id: '123e4567-e89b-12d3-a456-426614174001'
                };
                document.dispatchEvent(new CustomEvent('qr-scanned', { detail: testData }));
            }
        """)

        # Wait for session created confirmation
        await page.wait_for_selector("[data-testid='session-created']", timeout=5000)

        # Verify session is displayed
        session_text = await page.text_content("[data-testid='session-id']")
        assert "123e4567" in session_text

    async def test_menu_categories_displayed(self, page: Page):
        """Test menu categories are displayed"""
        await page.goto("http://localhost:3000/menu")

        # Wait for categories to load
        await page.wait_for_selector("[data-testid='menu-categories']")

        # Verify categories are displayed
        categories = await page.query_selector_all("[data-testid^='category-']")
        assert len(categories) > 0

        # Verify category names
        first_category_text = await page.text_content("[data-testid='category-0']")
        assert first_category_text is not None

    async def test_menu_items_displayed(self, page: Page):
        """Test menu items are displayed for a category"""
        await page.goto("http://localhost:3000/menu")

        # Wait for menu items to load
        await page.wait_for_selector("[data-testid='menu-items']")

        # Verify items are displayed
        items = await page.query_selector_all("[data-testid^='menu-item-']")
        assert len(items) > 0

        # Check first item has required fields
        await page.wait_for_selector("[data-testid='menu-item-0'] [data-testid='item-name']")
        await page.wait_for_selector("[data-testid='menu-item-0'] [data-testid='item-price']")
        await page.wait_for_selector("[data-testid='menu-item-0'] [data-testid='item-description']")

    async def test_add_item_to_cart(self, page: Page):
        """Test guest can add item to cart"""
        await page.goto("http://localhost:3000/menu")

        # Wait for menu items
        await page.wait_for_selector("[data-testid='menu-item-0']")

        # Click "Add to Cart" button
        await page.click("[data-testid='menu-item-0'] [data-testid='add-to-cart']")

        # Wait for cart to update
        await page.wait_for_selector("[data-testid='cart-count']", timeout=3000)

        # Verify cart count increased
        cart_count = await page.text_content("[data-testid='cart-count']")
        assert int(cart_count) > 0

    async def test_open_item_modal_and_add_modifiers(self, page: Page):
        """Test guest opens item modal and adds modifiers"""
        await page.goto("http://localhost:3000/menu")

        # Click on item to open modal
        await page.click("[data-testid='menu-item-0'] [data-testid='item-card']")

        # Wait for modal to open
        await page.wait_for_selector("[data-testid='item-modal']", timeout=3000)

        # Select modifier (e.g., size)
        await page.click("[data-testid='modifier-size-large']")

        # Add special instruction
        await page.fill("[data-testid='special-instructions']", "Extra cheese please")

        # Click "Add to Order"
        await page.click("[data-testid='modal-add-to-cart']")

        # Wait for modal to close
        await page.wait_for_selector_state(
            "[data-testid='item-modal']",
            state="hidden",
            timeout=3000
        )

        # Verify cart updated
        cart_count = await page.text_content("[data-testid='cart-count']")
        assert int(cart_count) > 0

    async def test_view_cart(self, page: Page):
        """Test guest can view cart"""
        await page.goto("http://localhost:3000")

        # Navigate to cart
        await page.click("[data-testid='cart-button']")

        # Wait for cart page to load
        await page.wait_for_selector("[data-testid='cart-page']", timeout=3000)

        # Verify cart items are displayed
        cart_items = await page.query_selector_all("[data-testid^='cart-item-']")
        assert len(cart_items) > 0

        # Verify total is displayed
        await page.wait_for_selector("[data-testid='cart-total']")
        cart_total = await page.text_content("[data-testid='cart-total']")
        assert "$" in cart_total

    async def test_submit_draft_success(self, page: Page):
        """Test guest can submit draft successfully"""
        await page.goto("http://localhost:3000/cart")

        # Wait for cart to load
        await page.wait_for_selector("[data-testid='cart-page']")

        # Click "Submit Draft" button
        await page.click("[data-testid='submit-draft']")

        # Wait for success message
        await page.wait_for_selector("[data-testid='draft-submitted-message']", timeout=5000)

        # Verify success message
        success_message = await page.text_content("[data-testid='draft-submitted-message']")
        assert "submitted" in success_message.lower()

    async def test_draft_status_updates_to_pending(self, page: Page):
        """Test draft status updates from draft to pending"""
        await page.goto("http://localhost:3000/cart")

        # Submit draft
        await page.click("[data-testid='submit-draft']")
        await page.wait_for_selector("[data-testid='draft-submitted-message']", timeout=5000)

        # Wait for status to update to pending
        await page.wait_for_selector("[data-testid='draft-status=pending']", timeout=5000)

        # Verify status is pending
        status_element = await page.query_selector("[data-testid='draft-status']")
        assert status_element is not None

    async def test_draft_status_updates_to_confirmed(self, page: Page):
        """Test draft status updates from pending to confirmed"""
        await page.goto("http://localhost:3000/drafts")

        # Simulate WebSocket status update
        await page.evaluate("""
            () => {
                // Simulate WebSocket message
                const message = {
                    type: 'draft_status_update',
                    draft_id: 'test-draft-id',
                    table_session_id: 'test-session-id',
                    status: 'confirmed',
                    timestamp: new Date().toISOString()
                };

                // Update UI
                document.dispatchEvent(new CustomEvent('draft-status', { detail: message }));
            }
        """)

        # Wait for confirmed status
        await page.wait_for_selector("[data-testid='draft-status=confirmed']", timeout=5000)

        # Verify confirmation message is displayed
        await page.wait_for_selector("[data-testid='draft-confirmed-message']", timeout=3000)
        confirmed_message = await page.text_content("[data-testid='draft-confirmed-message']")
        assert "confirmed" in confirmed_message.lower()

    async def test_draft_status_updates_to_rejected(self, page: Page):
        """Test draft status updates from pending to rejected"""
        await page.goto("http://localhost:3000/drafts")

        # Simulate WebSocket rejection
        await page.evaluate("""
            () => {
                const message = {
                    type: 'draft_rejected',
                    draft_id: 'test-draft-id',
                    table_session_id: 'test-session-id',
                    reason: 'Item out of stock',
                    timestamp: new Date().toISOString()
                };

                document.dispatchEvent(new CustomEvent('draft-status', { detail: message }));
            }
        """)

        # Wait for rejected status
        await page.wait_for_selector("[data-testid='draft-status=rejected']", timeout=5000)

        # Verify rejection message with reason
        await page.wait_for_selector("[data-testid='draft-rejected-message']", timeout=3000)
        rejected_message = await page.text_content("[data-testid='draft-rejected-message']")
        assert "out of stock" in rejected_message.lower()

    async def test_update_pending_draft_with_new_item(self, page: Page):
        """Test guest can update pending draft by adding item"""
        await page.goto("http://localhost:3000/drafts")

        # Simulate pending draft
        await page.evaluate("""
            () => {
                window.testDraftData = {
                    id: 'test-draft-id',
                    status: 'pending',
                    table_session_id: 'test-session-id',
                    version: 1
                };
            }
        """)

        # Navigate to menu
        await page.click("[data-testid='menu-link']")

        # Add item to cart
        await page.wait_for_selector("[data-testid='menu-item-0']")
        await page.click("[data-testid='menu-item-0'] [data-testid='add-to-cart']")

        # Click "Update Draft"
        await page.click("[data-testid='update-draft']")

        # Wait for update confirmation
        await page.wait_for_selector("[data-testid='draft-updated-message']", timeout=5000)

        update_message = await page.text_content("[data-testid='draft-updated-message']")
        assert "updated" in update_message.lower()

    async def test_version_conflict_on_update(self, page: Page):
        """Test version conflict when updating draft"""
        await page.goto("http://localhost:3000/drafts")

        # Simulate draft with old version
        await page.evaluate("""
            () => {
                window.testDraftData = {
                    id: 'test-draft-id',
                    status: 'pending',
                    version: 1  // Old version
                };
            }
        """)

        # Try to update
        await page.click("[data-testid='update-draft']")

        # Wait for conflict error message
        await page.wait_for_selector("[data-testid='version-conflict-error']", timeout=5000)

        error_message = await page.text_content("[data-testid='version-conflict-error']")
        assert "version" in error_message.lower() or "modified" in error_message.lower()

    async def test_offline_draft_persistence(self, page: Page):
        """Test draft is persisted offline with IndexedDB"""
        # Add item to cart
        await page.goto("http://localhost:3000/menu")
        await page.wait_for_selector("[data-testid='menu-item-0']")
        await page.click("[data-testid='menu-item-0'] [data-testid='add-to-cart']")

        # Simulate offline state
        await page.evaluate("() => window.navigator.onLine = false")
        await page.evaluate("() => window.dispatchEvent(new Event('offline'))")

        # Wait for offline indicator
        await page.wait_for_selector("[data-testid='offline-indicator']", timeout=3000)

        # Verify cart data is still visible (from IndexedDB)
        cart_count = await page.text_content("[data-testid='cart-count']")
        assert int(cart_count) > 0

    async def test_offline_to_online_sync(self, page: Page):
        """Test draft syncs when coming back online"""
        # Simulate offline state first
        await page.evaluate("() => window.navigator.onLine = false")
        await page.evaluate("() => window.dispatchEvent(new Event('offline'))")

        # Add item while offline
        await page.goto("http://localhost:3000/menu")
        await page.wait_for_selector("[data-testid='menu-item-0']")
        await page.click("[data-testid='menu-item-0'] [data-testid='add-to-cart']")

        # Simulate back online
        await page.evaluate("() => window.navigator.onLine = true")
        await page.evaluate("() => window.dispatchEvent(new Event('online'))")

        # Wait for sync indicator
        await page.wait_for_selector("[data-testid='sync-indicator']", timeout=5000)

        # Verify sync message
        sync_message = await page.text_content("[data-testid='sync-indicator']")
        assert "synced" in sync_message.lower() or "uploaded" in sync_message.lower()

    async def test_call_waiter_button(self, page: Page):
        """Test guest can call waiter"""
        await page.goto("http://localhost:3000/drafts")

        # Click "Call Waiter" button
        await page.click("[data-testid='call-waiter']")

        # Wait for confirmation
        await page.wait_for_selector("[data-testid='waiter-called-message']", timeout=3000)

        message = await page.text_content("[data-testid='waiter-called-message']")
        assert "waiter" in message.lower()

    async def test_complete_workflow_integration(self, page: Page):
        """Test complete workflow: scan → menu → cart → submit → confirm"""
        # 1. Scan QR (simulate)
        await page.goto("http://localhost:3000")
        await page.evaluate("""
            () => {
                const testData = {
                    table_id: '123e4567-e89b-12d3-a456-426614174000',
                    location_id: '123e4567-e89b-12d3-a456-426614174001'
                };
                document.dispatchEvent(new CustomEvent('qr-scanned', { detail: testData }));
            }
        """)
        await page.wait_for_selector("[data-testid='session-created']", timeout=5000)

        # 2. Browse menu
        await page.click("[data-testid='menu-link']")
        await page.wait_for_selector("[data-testid='menu-items']")

        # 3. Add item to cart
        await page.click("[data-testid='menu-item-0'] [data-testid='add-to-cart']")
        await page.wait_for_selector("[data-testid='cart-count']", timeout=3000)

        # 4. View cart and submit
        await page.click("[data-testid='cart-button']")
        await page.wait_for_selector("[data-testid='cart-page']", timeout=3000)
        await page.click("[data-testid='submit-draft']")
        await page.wait_for_selector("[data-testid='draft-submitted-message']", timeout=5000)

        # 5. Wait for pending status
        await page.wait_for_selector("[data-testid='draft-status=pending']", timeout=5000)

        # 6. Simulate confirmation via WebSocket
        await page.evaluate("""
            () => {
                const message = {
                    type: 'draft_confirmed',
                    draft_id: 'test-draft-id',
                    table_session_id: 'test-session-id',
                    order_id: 'order-123',
                    timestamp: new Date().toISOString()
                };
                document.dispatchEvent(new CustomEvent('draft-status', { detail: message }));
            }
        """)
        await page.wait_for_selector("[data-testid='draft-status=confirmed']", timeout=5000)

        # Verify final state
        await page.wait_for_selector("[data-testid='order-confirmation']", timeout=3000)
        confirmation_text = await page.text_content("[data-testid='order-confirmation']")
        assert "confirmed" in confirmation_text.lower()
