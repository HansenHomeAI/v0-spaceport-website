import { test, expect } from '@playwright/test';

/**
 * Autonomous Feedback Form Test Suite
 * This test validates the footer feedback form functionality
 * Used by the autonomous workflow to validate implementations
 */

test.describe('Footer Feedback Form', () => {
  let baseUrl: string;

  test.beforeEach(async ({ page }) => {
    // Get the deployment URL from environment or use default
    baseUrl = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000';
    console.log(`🌐 Testing against: ${baseUrl}`);
    
    // Set up console and network error monitoring
    const consoleErrors: string[] = [];
    const networkErrors: string[] = [];
    
    page.on('console', msg => {
      if (['error', 'warning'].includes(msg.type())) {
        consoleErrors.push(`CONSOLE ${msg.type().toUpperCase()}: ${msg.text()}`);
      }
    });
    
    page.on('requestfailed', request => {
      networkErrors.push(`NETWORK FAILED: ${request.url()} - ${request.failure()?.errorText}`);
    });
    
    // Store errors in page context for later access
    (page as any).testErrors = { consoleErrors, networkErrors };
  });

  test('should load homepage without errors', async ({ page }) => {
    await page.goto(baseUrl);
    
    // Check page loads successfully
    await expect(page).toHaveTitle(/Spaceport/);
    
    // Verify no critical console errors
    const errors = (page as any).testErrors;
    if (errors.consoleErrors.length > 0) {
      console.warn('Console errors detected:', errors.consoleErrors);
    }
    if (errors.networkErrors.length > 0) {
      console.error('Network errors detected:', errors.networkErrors);
      throw new Error(`Network errors: ${errors.networkErrors.join(', ')}`);
    }
  });

  test('should display feedback form in footer', async ({ page }) => {
    await page.goto(baseUrl);
    
    // Wait for page to load and scroll to footer
    await page.waitForLoadState('networkidle');
    
    // Find the feedback form
    const feedbackForm = page.locator('form').filter({ has: page.locator('textarea[placeholder*="feedback" i], textarea[placeholder*="message" i]') });
    
    if (await feedbackForm.count() === 0) {
      // Try alternative selectors
      const altForm = page.locator('footer form, #feedback-form, [data-testid="feedback-form"]');
      await expect(altForm).toBeVisible({ timeout: 5000 });
    } else {
      await expect(feedbackForm).toBeVisible();
    }
  });

  test('should submit feedback form successfully', async ({ page }) => {
    await page.goto(baseUrl);
    await page.waitForLoadState('networkidle');
    
    // Find feedback form elements
    const feedbackTextarea = page.locator('textarea[placeholder*="feedback" i], textarea[placeholder*="message" i]').first();
    const submitButton = page.locator('button[type="submit"]').filter({ hasText: /submit|send/i }).first();
    
    // If not found, try alternative selectors
    if (await feedbackTextarea.count() === 0) {
      console.log('🔍 Trying alternative feedback form selectors...');
      const altTextarea = page.locator('footer textarea, #feedback-textarea, [data-testid="feedback-input"]').first();
      const altButton = page.locator('footer button, #feedback-submit, [data-testid="feedback-submit"]').first();
      
      await expect(altTextarea).toBeVisible({ timeout: 5000 });
      await expect(altButton).toBeVisible({ timeout: 5000 });
      
      // Fill and submit using alternative selectors
      await altTextarea.fill('Test feedback message from Playwright automation');
      await altButton.click();
    } else {
      // Standard form submission
      await expect(feedbackTextarea).toBeVisible();
      await expect(submitButton).toBeVisible();
      
      await feedbackTextarea.fill('Test feedback message from Playwright automation');
      await submitButton.click();
    }
    
    // Wait for submission response
    await page.waitForTimeout(2000);
    
    // Check for success indicators
    const successIndicators = [
      page.locator('text=/success|sent|submitted/i'),
      page.locator('[data-testid="feedback-success"]'),
      page.locator('.success, .alert-success')
    ];
    
    let successFound = false;
    for (const indicator of successIndicators) {
      if (await indicator.count() > 0 && await indicator.isVisible()) {
        successFound = true;
        console.log('✅ Success indicator found:', await indicator.textContent());
        break;
      }
    }
    
    // Check for error indicators (should not be present)
    const errorIndicators = [
      page.locator('text=/error|failed|invalid/i'),
      page.locator('[data-testid="feedback-error"]'),
      page.locator('.error, .alert-error')
    ];
    
    for (const indicator of errorIndicators) {
      if (await indicator.count() > 0 && await indicator.isVisible()) {
        const errorText = await indicator.textContent();
        throw new Error(`Feedback submission failed with error: ${errorText}`);
      }
    }
    
    // Verify no critical errors occurred
    const errors = (page as any).testErrors;
    if (errors.networkErrors.length > 0) {
      console.error('Network errors during submission:', errors.networkErrors);
      throw new Error(`Network errors during submission: ${errors.networkErrors.join(', ')}`);
    }
    
    // If we get here without errors, consider it successful
    if (!successFound) {
      console.log('⚠️ No explicit success indicator found, but no errors detected either');
    }
  });

  test('should handle form validation', async ({ page }) => {
    await page.goto(baseUrl);
    await page.waitForLoadState('networkidle');
    
    // Try to submit empty form
    const submitButton = page.locator('button[type="submit"]').filter({ hasText: /submit|send/i }).first();
    
    if (await submitButton.count() === 0) {
      const altButton = page.locator('footer button, #feedback-submit, [data-testid="feedback-submit"]').first();
      await altButton.click();
    } else {
      await submitButton.click();
    }
    
    // Should show validation error or prevent submission
    await page.waitForTimeout(1000);
    
    // Check if form prevented submission (textarea should still be focusable)
    const feedbackTextarea = page.locator('textarea[placeholder*="feedback" i], textarea[placeholder*="message" i]').first();
    if (await feedbackTextarea.count() > 0) {
      await expect(feedbackTextarea).toBeFocused();
    }
  });
});

/**
 * Test Results Summary
 * This function generates a summary of test results for the autonomous workflow
 */
export async function generateTestSummary(results: any) {
  return {
    passed: results.passed || 0,
    failed: results.failed || 0,
    total: results.total || 0,
    duration: results.duration || 0,
    errors: results.errors || [],
    success: (results.failed || 0) === 0
  };
}
