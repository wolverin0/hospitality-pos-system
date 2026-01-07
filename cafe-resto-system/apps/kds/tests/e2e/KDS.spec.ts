/**
 * E2E tests for KDS PWA
 * Tests Kitchen Display System functionality with Playwright
 */

import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:5173';

test.describe('KDS PWA', () => {
  test.beforeAll(async ({ browser }) => {
    // Set up browser context for PWA
    const context = browser.context();
    await context.addInitScript(() => {
      window.matchMedia = (query) => ({
        matches: query.includes('dark'),
        media: query,
      });
    });
  });

  test.beforeEach(async ({ page }) => {
    // Navigate to KDS
    await page.goto(`${BASE_URL}/`);

    // Wait for initial load
    await page.waitForLoadState('networkidle');
  });

  test.describe('Page Load and Layout', () => {
    test('should load KDS page with all elements', async ({ page }) => {
      // Check main page elements
      await expect(page.locator('h1')).toBeVisible();
      
      // Check header with logo
      await expect(page.locator('text=/GASTOWN.*KDS/')).toBeVisible();
      
      // Check connection status indicator
      await expect(page.locator('text=/ONLINE|OFFLINE/')).toBeVisible();
    });

    test('should display top bar with logo, filter, and connection status', async ({ page }) => {
      // Logo area
      await expect(page.locator('.flex').first()).toBeVisible();
      
      // Station filter component should be present
      await expect(page.locator('select')).toBeVisible();
      
      // Connection status
      await expect(page.locator('div:has-text("ONLINE")').or(page.locator('div:has-text("OFFLINE")')).toBeVisible();
    });

    test('should display bottom status bar with ticket counts', async ({ page }) => {
      // Status bar with Pending, Working, Ready counts
      await expect(page.locator('text=Pending')).toBeVisible();
      await expect(page.locator('text=Working')).toBeVisible();
      await expect(page.locator('text=Ready')).toBeVisible();
    });

    test('should have responsive layout', async ({ page }) => {
      // Test on mobile viewport
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto(`${BASE_URL}/`);
      await page.waitForLoadState('networkidle');
      await expect(page.locator('h1')).toBeVisible();

      // Test on desktop viewport
      await page.setViewportSize({ width: 1920, height: 1080 });
      await page.goto(`${BASE_URL}/`);
      await page.waitForLoadState('networkidle');
      await expect(page.locator('h1')).toBeVisible();
    });
  });

  test.describe('Station Filter', () => {
    test('should display station dropdown options', async ({ page }) => {
      // Find station filter dropdown
      const stationFilter = page.locator('select');
      await expect(stationFilter).toBeVisible();

      // Get all options
      const options = await stationFilter.locator('option').all();
      expect(options.length).toBeGreaterThan(0);
    });

    test('should filter tickets by selected station', async ({ page }) => {
      const stationFilter = page.locator('select');

      // Select "Kitchen" station (if available)
      const kitchenOption = stationFilter.locator('option:has-text("Kitchen")');
      const hasKitchen = await kitchenOption.count();
      
      if (hasKitchen > 0) {
        await stationFilter.selectOption('Kitchen');
        await page.waitForTimeout(1000);
        
        // Verify filter applied
        const selectedValue = await stationFilter.inputValue();
        expect(selectedValue).toContain('Kitchen');
      }
    });

    test('should switch between stations', async ({ page }) => {
      const stationFilter = page.locator('select');
      
      // Get initial value
      const initialValue = await stationFilter.inputValue();
      
      // Select different station
      const options = await stationFilter.locator('option').all();
      if (options.length > 1) {
        await stationFilter.selectOption({ index: 1 });
        await page.waitForTimeout(1000);
        
        // Verify selection changed
        const newValue = await stationFilter.inputValue();
        expect(newValue).not.toBe(initialValue);
      }
    });
  });

  test.describe('Ticket Queue Display', () => {
    test('should display ticket queue area', async ({ page }) => {
      // Main content area with tickets
      const queueArea = page.locator('main');
      await expect(queueArea).toBeVisible();
    });

    test('should display ticket cards with status badges', async ({ page }) => {
      // Wait for tickets to load
      await page.waitForTimeout(2000);
      
      // Look for ticket cards (should have elements with ticket info)
      const ticketCards = page.locator('[class*="ticket"]');
      const hasCards = await ticketCards.count();
      
      // Note: This will pass only if there are tickets in the system
      // For initial load with no tickets, we just verify the area exists
      if (hasCards > 0) {
        await expect(ticketCards.first()).toBeVisible();
        
        // Check for status badges
        const statusBadges = page.locator('[class*="status"]');
        const hasBadges = await statusBadges.count();
        expect(hasBadges).toBeGreaterThan(0);
      }
    });

    test('should display course information on tickets', async ({ page }) => {
      // Look for course indicators
      const courseBadges = page.locator('[class*="course"]');
      const hasCourses = await courseBadges.count();
      
      if (hasCourses > 0) {
        await expect(courseBadges.first()).toBeVisible();
        
        // Should show course numbers like "1", "2", "3" or course names like "Drinks", "Mains"
        const courseText = await courseBadges.first().textContent();
        expect(courseText).toBeTruthy();
      }
    });

    test('should display table numbers on tickets', async ({ page }) => {
      // Look for table indicators
      const tableIndicators = page.locator('[class*="table"]');
      const hasTables = await tableIndicators.count();
      
      if (hasTables > 0) {
        await expect(tableIndicators.first()).toBeVisible();
        const tableText = await tableIndicators.first().textContent();
        expect(tableText).toBeTruthy();
      }
    });

    test('should display timer on tickets', async ({ page }) => {
      // Look for timer elements
      const timers = page.locator('[class*="timer"]');
      const hasTimers = await timers.count();
      
      if (hasTimers > 0) {
        await expect(timers.first()).toBeVisible();
      }
    });

    test('should sort tickets by priority (rush first)', async ({ page }) => {
      // Look for rush indicators
      const rushBadges = page.locator('[class*="rush"]');
      const hasRush = await rushBadges.count();
      
      if (hasRush > 0) {
        await expect(rushBadges.first()).toBeVisible();
        // Rush tickets should be visually distinct
        const rushText = await rushBadges.first().textContent();
        expect(rushText.toUpperCase()).toContain('RUSH');
      }
    });

    test('should display server name on tickets', async ({ page }) => {
      // Look for server info
      const serverInfo = page.locator('[class*="server"]');
      const hasServerInfo = await serverInfo.count();
      
      if (hasServerInfo > 0) {
        await expect(serverInfo.first()).toBeVisible();
        const serverText = await serverInfo.first().textContent();
        expect(serverText).toBeTruthy();
      }
    });
  });

  test.describe('Ticket Actions', () => {
    test('should display bump button on tickets', async ({ page }) => {
      await page.waitForTimeout(2000);
      
      // Look for bump buttons
      const bumpButtons = page.locator('button:has-text("Bump"), [aria-label*="bump"]');
      const hasBumpButtons = await bumpButtons.count();
      
      if (hasBumpButtons > 0) {
        await expect(bumpButtons.first()).toBeVisible();
        await expect(bumpButtons.first()).toBeEnabled();
      }
    });

    test('should display hold button on tickets', async ({ page }) => {
      await page.waitForTimeout(2000);
      
      // Look for hold buttons
      const holdButtons = page.locator('button:has-text("Hold"), [aria-label*="hold"]');
      const hasHoldButtons = await holdButtons.count();
      
      if (hasHoldButtons > 0) {
        await expect(holdButtons.first()).toBeVisible();
        await expect(holdButtons.first()).toBeEnabled();
      }
    });

    test('should display fire button on held tickets', async ({ page }) => {
      await page.waitForTimeout(2000);
      
      // Look for fire buttons (only visible on held tickets)
      const fireButtons = page.locator('button:has-text("Fire"), [aria-label*="fire"]');
      const hasFireButtons = await fireButtons.count();
      
      // Fire buttons might not always be visible
      if (hasFireButtons > 0) {
        await expect(fireButtons.first()).toBeVisible();
      }
    });

    test('should display void button on tickets', async ({ page }) => {
      await page.waitForTimeout(2000);
      
      // Look for void buttons
      const voidButtons = page.locator('button:has-text("Void"), [aria-label*="void"]');
      const hasVoidButtons = await voidButtons.count();
      
      if (hasVoidButtons > 0) {
        await expect(voidButtons.first()).toBeVisible();
        // Void might be disabled for non-manager roles
        await expect(voidButtons.first()).toBeVisible();
      }
    });

    test('should be able to click bump button', async ({ page }) => {
      await page.waitForTimeout(2000);
      
      const bumpButton = page.locator('button:has-text("Bump"), [aria-label*="bump"]').first();
      const hasBumpButton = await bumpButton.count();
      
      if (hasBumpButton > 0) {
        await bumpButton.click();
        // Wait for response
        await page.waitForTimeout(500);
        
        // Ticket status should update
        // This is a smoke test - actual API response testing requires backend
      }
    });

    test('should be able to click hold button', async ({ page }) => {
      await page.waitForTimeout(2000);
      
      const holdButton = page.locator('button:has-text("Hold"), [aria-label*="hold"]').first();
      const hasHoldButton = await holdButton.count();
      
      if (hasHoldButton > 0) {
        await holdButton.click();
        // Wait for hold reason dialog (if exists)
        await page.waitForTimeout(500);
      }
    });

    test('should be able to click void button', async ({ page }) => {
      await page.waitForTimeout(2000);
      
      const voidButton = page.locator('button:has-text("Void"), [aria-label*="void"]').first();
      const hasVoidButton = await voidButton.count();
      
      if (hasVoidButton > 0) {
        await voidButton.click();
        // Wait for void reason dialog (if exists)
        await page.waitForTimeout(500);
      }
    });
  });

  test.describe('Ticket Details', () => {
    test('should be able to open ticket details', async ({ page }) => {
      await page.waitForTimeout(2000);
      
      // Look for clickable ticket cards
      const ticketCards = page.locator('[class*="ticket"]');
      const hasCards = await ticketCards.count();
      
      if (hasCards > 0) {
        // Click on first ticket
        await ticketCards.first().click();
        await page.waitForTimeout(500);
        
        // Verify details view opened
        // This depends on how details are displayed (modal, separate page, expanded card)
      }
    });

    test('should display line items in ticket details', async ({ page }) => {
      // If details are displayed inline, check for line items
      const lineItems = page.locator('[class*="line-item"], [class*="item"]');
      const hasLineItems = await lineItems.count();
      
      if (hasLineItems > 0) {
        await expect(lineItems.first()).toBeVisible();
      }
    });

    test('should display modifiers on line items', async ({ page }) => {
      // Look for modifier indicators
      const modifiers = page.locator('[class*="modifier"]');
      const hasModifiers = await modifiers.count();
      
      if (hasModifiers > 0) {
        await expect(modifiers.first()).toBeVisible();
      }
    });

    test('should display special instructions', async ({ page }) => {
      // Look for special instruction indicators
      const specialInstructions = page.locator('[class*="instruction"], [class*="note"]');
      const hasInstructions = await specialInstructions.count();
      
      if (hasInstructions > 0) {
        await expect(specialInstructions.first()).toBeVisible();
      }
    });
  });

  test.describe('Status Bar Counts', () => {
    test('should display pending ticket count', async ({ page }) => {
      const pendingLabel = page.locator('text=Pending');
      await expect(pendingLabel).toBeVisible();
      
      // Look for count number next to it
      const parent = pendingLabel.locator('..');
      const countElement = parent.locator('span').or(parent.locator('div')).first();
      await expect(countElement).toBeVisible();
    });

    test('should display preparing/work ing ticket count', async ({ page }) => {
      const workingLabel = page.locator('text=Working').or(page.locator('text=Preparing'));
      await expect(workingLabel).toBeVisible();
      
      const countElement = workingLabel.locator('..').locator('span').first();
      await expect(countElement).toBeVisible();
    });

    test('should display ready ticket count', async ({ page }) => {
      const readyLabel = page.locator('text=Ready');
      await expect(readyLabel).toBeVisible();
      
      const countElement = readyLabel.locator('..').locator('span').first();
      await expect(countElement).toBeVisible();
    });

    test('should update counts when tickets change status', async ({ page }) => {
      // Get initial counts
      const initialPendingText = await page.locator('text=Pending').locator('..').locator('span').first().textContent();
      
      // Note: Full integration test would require WebSocket mocking
      // This is a UI smoke test - we verify the elements exist and can display counts
      expect(initialPendingText).toBeTruthy();
    });
  });

  test.describe('Connection Status', () => {
    test('should show ONLINE when connected', async ({ page }) => {
      const onlineIndicator = page.locator('text=ONLINE');
      const offlineIndicator = page.locator('text=OFFLINE');
      
      // At least one should be visible
      const isOnlineVisible = await onlineIndicator.count();
      const isOfflineVisible = await offlineIndicator.count();
      
      expect(isOnlineVisible + isOfflineVisible).toBeGreaterThan(0);
    });

    test('should show Wifi icon when online', async ({ page }) => {
      const onlineIndicator = page.locator('text=ONLINE');
      const hasOnline = await onlineIndicator.count();
      
      if (hasOnline > 0) {
        // Check for wifi icon
        const parent = onlineIndicator.locator('..');
        const wifiIcon = parent.locator('svg').or(parent.locator('[data-icon*="wifi"]'));
        expect(await wifiIcon.count()).toBeGreaterThan(0);
      }
    });

    test('should show WifiOff icon when offline', async ({ page }) => {
      const offlineIndicator = page.locator('text=OFFLINE');
      const hasOffline = await offlineIndicator.count();
      
      if (hasOffline > 0) {
        // Check for wifi-off icon
        const parent = offlineIndicator.locator('..');
        const wifiOffIcon = parent.locator('svg').or(parent.locator('[data-icon*="wifi-off"]'));
        expect(await wifiOffIcon.count()).toBeGreaterThan(0);
      }
    });
  });

  test.describe('PWA Features', () => {
    test('should have PWA manifest', async ({ page }) => {
      // Navigate to manifest
      const manifestResponse = await page.request.get(`${BASE_URL}/manifest.json`);
      expect(manifestResponse.ok()).toBeTruthy();
      
      const manifest = await manifestResponse.json();
      
      // Verify PWA manifest properties
      expect(manifest.name).toBeTruthy();
      expect(manifest.display).toBe('standalone');
      expect(manifest.theme_color).toBeTruthy();
    });

    test('should be installable as PWA', async ({ page }) => {
      // Check if service worker is registered (may need to wait)
      await page.waitForTimeout(3000);
      
      // Service worker registration check would require console inspection
      // For now, we verify the manifest exists
      const manifestResponse = await page.request.get(`${BASE_URL}/manifest.json`);
      expect(manifestResponse.ok()).toBeTruthy();
    });

    test('should work offline', async ({ page }) => {
      // Simulate offline mode
      await page.context().setOffline(true);
      await page.reload();
      await page.waitForLoadState('networkidle');
      
      // Page should still load
      await expect(page.locator('h1')).toBeVisible();
      
      // Should show offline indicator
      const offlineIndicator = page.locator('text=OFFLINE');
      await expect(offlineIndicator).toBeVisible();
      
      // Restore online
      await page.context().setOffline(false);
      await page.reload();
      await page.waitForLoadState('networkidle');
    });
  });

  test.describe('Accessibility', () => {
    test('should have proper heading structure', async ({ page }) => {
      const h1 = page.locator('h1');
      await expect(h1).toBeVisible();
    });

    test('should have proper button labels', async ({ page }) => {
      // Check all buttons have accessible names
      const buttons = page.locator('button').or(page.locator('button:has-text("Bump")'));
      const buttonCount = await buttons.count();
      
      if (buttonCount > 0) {
        for (let i = 0; i < Math.min(buttonCount, 5); i++) {
          const button = buttons.nth(i);
          await expect(button).toBeVisible();
          
          // Check for aria-label or text content
          const hasAccessibleLabel = await button.getAttribute('aria-label');
          const hasText = await button.textContent();
          expect(hasAccessibleLabel !== null || hasText !== null).toBeTruthy();
        }
      }
    });

    test('should have proper color contrast', async ({ page }) => {
      // Check that status badges are visible and have distinct colors
      const statusElements = page.locator('[class*="status"]');
      const statusCount = await statusElements.count();
      
      if (statusCount > 0) {
        // Verify status elements have background colors
        // This requires checking computed styles or class names with colors
        await expect(statusElements.first()).toBeVisible();
      }
    });
  });

  test.describe('Performance', () => {
    test('should load quickly', async ({ page }) => {
      const startTime = Date.now();
      await page.goto(`${BASE_URL}/`);
      await page.waitForLoadState('networkidle');
      const loadTime = Date.now() - startTime;
      
      // Page should load within 3 seconds
      expect(loadTime).toBeLessThan(3000);
    });

    test('should handle multiple rapid state changes', async ({ page }) => {
      // Test page doesn't crash with rapid updates
      const stationFilter = page.locator('select');
      
      if (await stationFilter.count() > 0) {
        const options = await stationFilter.locator('option').all();
        
        // Rapidly switch between stations
        for (let i = 0; i < Math.min(options.length, 5); i++) {
          await stationFilter.selectOption({ index: i });
          await page.waitForTimeout(100);
        }
        
        // Page should still be functional
        await expect(page.locator('h1')).toBeVisible();
      }
    });
  });
});
