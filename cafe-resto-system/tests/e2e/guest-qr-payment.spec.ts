/**
 * E2E Playwright Tests for Guest QR Payment Flow
 */

import { test, expect } from '@playwright/test';
import { v4 as uuidv4 } from 'uuid';

// Mock backend base URL
const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

// Test data
const TEST_ORDER_ID = uuidv4();
const TEST_TABLE_SESSION_ID = uuidv4();

test.describe('Guest QR Payment Flow', () => {

  test.beforeAll(async () => {
    console.log('Starting E2E tests for guest QR payment');
  });

  test.afterAll(async () => {
    console.log('Finished E2E tests for guest QR payment');
  });

  test('Happy Path - Complete QR Payment', async ({ page }) => {
    // Generate test order ID
    const orderId = TEST_ORDER_ID;
    const tableSessionId = TEST_TABLE_SESSION_ID;

    // Navigate to QR payment page
    await page.goto(`${BASE_URL}/pay/qr-payment?order_id=${orderId}&table_session_id=${tableSessionId}`);

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Verify we're on the QR payment page
    await expect(page).toHaveTitle(/QR Payment/i);

    // Verify tip selection options are visible
    const tipButtons = page.locator('[data-testid="tip-button"]');
    await expect(tipButtons).toHaveCount(4); // 0%, 10%, 15%, 20%

    // Select 15% tip
    await tipButtons.nth(2).click(); // Third button (15%)
    await expect(tipButtons.nth(2)).toHaveClass(/bg-primary/);

    // Click "Pay Now" button
    const payNowButton = page.locator('[data-testid="pay-now-button"]');
    await payNowButton.click();

    // Wait for QR code to display
    const qrCodeContainer = page.locator('[data-testid="qr-code-container"]');
    await expect(qrCodeContainer).toBeVisible({ timeout: 5000 });

    // Verify QR code is displayed (should be an SVG canvas or image)
    const qrCode = page.locator('canvas, svg, img').first();
    await expect(qrCode).toBeVisible();

    // Verify payment status is "pending"
    const paymentStatus = page.locator('[data-testid="payment-status"]');
    await expect(paymentStatus).toContainText(/pending|waiting/i);

    // Verify "Scan with Mercado Pago App" button is visible
    const mpAppButton = page.locator('[data-testid="mercadopago-app-button"]');
    await expect(mpAppButton).toBeVisible();
    await expect(mpAppButton).toHaveAttribute('href');

    // Simulate payment completion (in real scenario, this would be from webhook)
    // For now, we'll verify the UI elements that would be shown

    // Verify total amount displayed (should include tip)
    const totalAmount = page.locator('[data-testid="total-amount"]');
    await expect(totalAmount).toBeVisible();
    await expect(totalAmount).toContainText(/$/);

    // Verify expiry time is displayed
    const expiryTime = page.locator('[data-testid="expiry-time"]');
    await expect(expiryTime).toBeVisible();
  });

  test('QR Code Expiry', async ({ page }) => {
    const orderId = uuidv4();
    const tableSessionId = uuidv4();

    // Navigate to QR payment page
    await page.goto(`${BASE_URL}/pay/qr-payment?order_id=${orderId}&table_session_id=${tableSessionId}`);

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Click "Pay Now" to create payment intent
    const payNowButton = page.locator('[data-testid="pay-now-button"]');
    await payNowButton.click();

    // Mock API to return 410 GONE (expired QR code)
    // Note: In real testing, this would require test backend or API mocking
    // Here we'll just verify the UI elements that would handle expiry

    // Verify QR code is displayed initially
    const qrCodeContainer = page.locator('[data-testid="qr-code-container"]');
    await expect(qrCodeContainer).toBeVisible();

    // In a real test with mocked API returning 410:
    // - Verify expiry message is displayed
    // - Verify "Try Again" button appears
    // - Verify error message mentions QR code expiration

    // Note: Actual expiry testing requires backend mocking or test database
    console.log('QR code expiry test completed (requires backend mocking for full verification)');
  });

  test('Payment Failure', async ({ page }) => {
    const orderId = uuidv4();
    const tableSessionId = uuidv4();

    // Navigate to QR payment page
    await page.goto(`${BASE_URL}/pay/qr-payment?order_id=${orderId}&table_session_id=${tableSessionId}`);

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Click "Pay Now" button
    const payNowButton = page.locator('[data-testid="pay-now-button"]');
    await payNowButton.click();

    // Wait for QR code to display
    const qrCodeContainer = page.locator('[data-testid="qr-code-container"]');
    await expect(qrCodeContainer).toBeVisible();

    // In a real test with mocked failed payment:
    // - Verify failure message is displayed
    // - Verify error icon is shown
    // - Verify "Try Again" button appears
    // - Verify specific error message (e.g., "Payment declined by bank")

    // Note: Actual failure testing requires backend mocking
    console.log('Payment failure test completed (requires backend mocking for full verification)');
  });

  test('Tip Selection Flow', async ({ page }) => {
    const orderId = uuidv4();
    const tableSessionId = uuidv4();

    // Navigate to QR payment page
    await page.goto(`${BASE_URL}/pay/qr-payment?order_id=${orderId}&table_session_id=${tableSessionId}`);

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Verify all tip buttons are present
    const tipButtons = page.locator('[data-testid="tip-button"]');
    await expect(tipButtons).toHaveCount(4);

    // Verify tip amounts (0%, 10%, 15%, 20%)
    await expect(tipButtons.nth(0)).toContainText('0%');
    await expect(tipButtons.nth(1)).toContainText('10%');
    await expect(tipButtons.nth(2)).toContainText('15%');
    await expect(tipButtons.nth(3)).toContainText('20%');

    // Test selecting each tip option
    for (let i = 0; i < 4; i++) {
      // Clear selection by clicking the first button again
      await tipButtons.first().click();

      // Click the ith tip button
      await tipButtons.nth(i).click();

      // Verify it's selected (has primary background color)
      await expect(tipButtons.nth(i)).toHaveClass(/bg-primary/);

      // Verify other buttons are not selected
      for (let j = 0; j < 4; j++) {
        if (i !== j) {
          await expect(tipButtons.nth(j)).not.toHaveClass(/bg-primary/);
        }
      }
    }
  });

  test('Responsive Design - Mobile View', async ({ page, context }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 812 });

    const orderId = uuidv4();
    const tableSessionId = uuidv4();

    // Navigate to QR payment page
    await page.goto(`${BASE_URL}/pay/qr-payment?order_id=${orderId}&table_session_id=${tableSessionId}`);

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Verify QR code is readable on mobile (not too small)
    const qrCode = page.locator('canvas, svg, img').first();
    await expect(qrCode).toBeVisible();

    // Get QR code bounding box
    const qrBox = await qrCode.boundingBox();
    expect(qrBox.width).toBeGreaterThan(200); // At least 200px wide
    expect(qrBox.height).toBeGreaterThan(200); // At least 200px tall

    // Verify buttons are tappable (minimum touch target size)
    const payNowButton = page.locator('[data-testid="pay-now-button"]');
    const buttonBox = await payNowButton.boundingBox();
    expect(buttonBox.height).toBeGreaterThanOrEqual(44); // iOS touch target minimum
    expect(buttonBox.width).toBeGreaterThanOrEqual(44);

    // Verify tip buttons are also tappable
    const tipButtons = page.locator('[data-testid="tip-button"]');
    const tipBox = await tipButtons.first().boundingBox();
    expect(tipBox.height).toBeGreaterThanOrEqual(44);
    expect(tipBox.width).toBeGreaterThanOrEqual(44);
  });

  test('Dark Mode Styling', async ({ page }) => {
    // Enable dark mode (simulate via class or system preference)
    await page.emulateMedia({ colorScheme: 'dark' });

    const orderId = uuidv4();
    const tableSessionId = uuidv4();

    // Navigate to QR payment page
    await page.goto(`${BASE_URL}/pay/qr-payment?order_id=${orderId}&table_session_id=${tableSessionId}`);

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Verify background is dark
    const body = page.locator('body');
    const backgroundColor = await body.evaluate((el) => {
      return window.getComputedStyle(el).backgroundColor;
    });
    expect(backgroundColor).toMatch(/rgb\(1[89], 89, 89\)|rgba\(1[89], 89, 89/|#[0-9a-f]{3,6}/i);

    // Verify QR code has good contrast
    const qrCode = page.locator('canvas, svg, img').first();
    await expect(qrCode).toBeVisible();

    // Verify text is readable (light text on dark background)
    const paymentStatus = page.locator('[data-testid="payment-status"]');
    const textColor = await paymentStatus.evaluate((el) => {
      return window.getComputedStyle(el).color;
    });
    expect(textColor).toMatch(/rgb\(2[35-55], 2[35-55], 2[35-55]\)|rgba\(2[35-55], 2[35-55], 2[35-55]/);
  });

  test('Payment Success and Auto-Redirect', async ({ page }) => {
    const orderId = uuidv4();
    const tableSessionId = uuidv4();

    // Navigate to QR payment page
    await page.goto(`${BASE_URL}/pay/qr-payment?order_id=${orderId}&table_session_id=${tableSessionId}`);

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Click "Pay Now"
    await page.locator('[data-testid="pay-now-button"]').click();

    // Wait for QR code
    await expect(page.locator('[data-testid="qr-code-container"]')).toBeVisible();

    // In real scenario, after payment completes:
    // - Success message should appear
    // - Auto-redirect to table session page after 3 seconds
    // - Verify URL changed to /table?table_session_id={tableSessionId}

    // Note: Actual redirect testing requires successful payment simulation
    console.log('Payment success test completed (requires backend mocking for full verification)');
  });

  test('Error Handling - Invalid Parameters', async ({ page }) => {
    // Navigate with missing order_id
    await page.goto(`${BASE_URL}/pay/qr-payment?table_session_id=${TEST_TABLE_SESSION_ID}`);

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Verify error message is displayed
    const errorMessage = page.locator('[data-testid="error-message"]');
    await expect(errorMessage).toBeVisible();
    await expect(errorMessage).toContainText(/order.*id.*required|missing.*parameter/i);
  });

  test('Loading States', async ({ page }) => {
    const orderId = uuidv4();
    const tableSessionId = uuidv4();

    // Navigate to QR payment page
    await page.goto(`${BASE_URL}/pay/qr-payment?order_id=${orderId}&table_session_id=${tableSessionId}`);

    // Click "Pay Now"
    await page.locator('[data-testid="pay-now-button"]').click();

    // Verify loading state is shown
    const loadingSpinner = page.locator('[data-testid="loading-spinner"]');
    await expect(loadingSpinner).toBeVisible();

    // Wait for QR code to appear (loading should disappear)
    await expect(page.locator('[data-testid="qr-code-container"]')).toBeVisible({ timeout: 5000 });

    // Verify loading spinner is gone
    await expect(loadingSpinner).not.toBeVisible();
  });

  test('QR Code Accessibility', async ({ page }) => {
    const orderId = uuidv4();
    const tableSessionId = uuidv4();

    // Navigate to QR payment page
    await page.goto(`${BASE_URL}/pay/qr-payment?order_id=${orderId}&table_session_id=${tableSessionId}`);

    // Click "Pay Now"
    await page.locator('[data-testid="pay-now-button"]').click();

    // Wait for QR code
    await page.waitForSelector('[data-testid="qr-code-container"]');

    // Verify QR code has alt text or aria-label
    const qrCode = page.locator('canvas, svg, img').first();
    const altText = await qrCode.getAttribute('alt');
    const ariaLabel = await qrCode.getAttribute('aria-label');

    expect(altText || ariaLabel).toBeTruthy();
  });

  test('Payment Amount Verification', async ({ page }) => {
    const orderId = uuidv4();
    const tableSessionId = uuidv4();

    // Navigate to QR payment page
    await page.goto(`${BASE_URL}/pay/qr-payment?order_id=${orderId}&table_session_id=${tableSessionId}`);

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Select 15% tip
    await page.locator('[data-testid="tip-button"]').nth(2).click();

    // Verify total amount is updated
    const totalAmount = page.locator('[data-testid="total-amount"]');
    await expect(totalAmount).toBeVisible();

    // Verify breakdown is shown (subtotal + tip + total)
    const subtotal = page.locator('[data-testid="subtotal"]');
    const tipAmount = page.locator('[data-testid="tip-amount"]');
    const total = page.locator('[data-testid="total-amount"]');

    await expect(subtotal).toBeVisible();
    await expect(tipAmount).toBeVisible();
    await expect(total).toBeVisible();
  });

  test('Retry Flow - Expired QR', async ({ page }) => {
    const orderId = uuidv4();
    const tableSessionId = uuidv4();

    // Navigate to QR payment page
    await page.goto(`${BASE_URL}/pay/qr-payment?order_id=${orderId}&table_session_id=${tableSessionId}`);

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Click "Pay Now"
    await page.locator('[data-testid="pay-now-button"]').click();

    // In real scenario with expired QR (410 response):
    // - Verify expiry message: "QR code has expired"
    // - Verify "Try Again" button is visible
    // - Click "Try Again" button
    // - Verify new QR code is generated
    // - Verify new QR code is different from expired one

    console.log('Retry flow test completed (requires backend mocking for full verification)');
  });

  test('WebSocket Connection (Optional)', async ({ page }) => {
    const orderId = uuidv4();
    const tableSessionId = uuidv4();

    // Navigate to QR payment page
    await page.goto(`${BASE_URL}/pay/qr-payment?order_id=${orderId}&table_session_id=${tableSessionId}`);

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // In real scenario with WebSocket:
    // - Verify WebSocket connection established
    // - Listen for payment status updates
    // - Verify UI updates when status changes
    // - Verify connection is closed after payment completes

    console.log('WebSocket test completed (requires WebSocket server for full verification)');
  });
});
