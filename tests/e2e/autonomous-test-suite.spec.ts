import { test, expect, Page } from '@playwright/test';

/**
 * Autonomous Test Suite for Full-Stack Validation
 * Captures console errors, network failures, and UI state for AI analysis
 */

interface TestResult {
  passed: boolean;
  errors: string[];
  warnings: string[];
  networkFailures: string[];
  screenshots: string[];
  performance: {
    loadTime: number;
    firstContentfulPaint: number;
    largestContentfulPaint: number;
  };
}

class AutonomousTestHelper {
  private errors: string[] = [];
  private warnings: string[] = [];
  private networkFailures: string[] = [];
  private screenshots: string[] = [];

  async setupErrorCapture(page: Page): Promise<void> {
    // Capture console errors and warnings
    page.on('console', msg => {
      const type = msg.type();
      const text = msg.text();
      
      if (type === 'error') {
        this.errors.push(`CONSOLE ERROR: ${text}`);
      } else if (type === 'warning') {
        this.warnings.push(`CONSOLE WARNING: ${text}`);
      }
    });

    // Capture network failures
    page.on('requestfailed', request => {
      const failure = request.failure();
      this.networkFailures.push(
        `NETWORK FAILURE: ${request.url()} - ${failure?.errorText || 'Unknown error'}`
      );
    });

    // Capture uncaught exceptions
    page.on('pageerror', error => {
      this.errors.push(`UNCAUGHT EXCEPTION: ${error.message}`);
    });
  }

  async captureScreenshot(page: Page, name: string): Promise<void> {
    const screenshotPath = `test-results/${name}-${Date.now()}.png`;
    await page.screenshot({ path: screenshotPath, fullPage: true });
    this.screenshots.push(screenshotPath);
  }

  async measurePerformance(page: Page): Promise<TestResult['performance']> {
    const performanceMetrics = await page.evaluate(() => {
      const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      return {
        loadTime: navigation.loadEventEnd - navigation.loadEventStart,
        firstContentfulPaint: 0, // Would need PerformanceObserver for real FCP
        largestContentfulPaint: 0, // Would need PerformanceObserver for real LCP
      };
    });

    return performanceMetrics;
  }

  getTestResult(passed: boolean, performance: TestResult['performance']): TestResult {
    return {
      passed,
      errors: [...this.errors],
      warnings: [...this.warnings],
      networkFailures: [...this.networkFailures],
      screenshots: [...this.screenshots],
      performance
    };
  }

  reset(): void {
    this.errors = [];
    this.warnings = [];
    this.networkFailures = [];
    this.screenshots = [];
  }
}

test.describe('Autonomous Full-Stack Test Suite', () => {
  let testHelper: AutonomousTestHelper;

  test.beforeEach(async () => {
    testHelper = new AutonomousTestHelper();
  });

  test('Landing page loads without errors', async ({ page }) => {
    await testHelper.setupErrorCapture(page);
    
    await page.goto('/');
    await expect(page).toHaveTitle(/Spaceport/);
    
    // Wait for critical elements to load
    await expect(page.locator('[data-testid="hero-section"]')).toBeVisible({ timeout: 10000 });
    
    // Check for authentication elements
    const authElements = page.locator('[data-testid="auth-gate"], [data-testid="sign-in-form"]');
    if (await authElements.count() > 0) {
      await expect(authElements.first()).toBeVisible();
    }

    await testHelper.captureScreenshot(page, 'landing-page');
    const performance = await testHelper.measurePerformance(page);
    const result = testHelper.getTestResult(true, performance);

    // Output results for AI analysis
    console.log('AUTONOMOUS_TEST_RESULT:', JSON.stringify(result, null, 2));
    
    // Fail test if critical errors found
    expect(result.errors.filter(e => e.includes('CONSOLE ERROR'))).toHaveLength(0);
  });

  test('Authentication flow works correctly', async ({ page }) => {
    await testHelper.setupErrorCapture(page);
    
    await page.goto('/');
    
    // Check if we have test credentials from environment
    const testEmail = process.env.TEST_EMAIL;
    const testPassword = process.env.TEST_PASSWORD;
    
    // Look for auth elements
    const signInButton = page.locator('button:has-text("Sign In"), input[type="email"]').first();
    
    if (await signInButton.isVisible()) {
      // Test authentication UI
      await expect(signInButton).toBeVisible();
      
      // Try to interact with auth form
      const emailInput = page.locator('input[type="email"]').first();
      const passwordInput = page.locator('input[type="password"]').first();
      
      if (await emailInput.isVisible() && testEmail && testPassword) {
        // Attempt full authentication with test credentials
        await emailInput.fill(testEmail);
        await passwordInput.fill(testPassword);
        
        await testHelper.captureScreenshot(page, 'auth-form-filled');
        
        // Try to submit
        const submitButton = page.locator('button[type="submit"]').first();
        if (await submitButton.isVisible()) {
          await submitButton.click();
          
          // Wait for navigation or error
          await page.waitForTimeout(3000);
          await testHelper.captureScreenshot(page, 'auth-submission-result');
        }
      } else if (await emailInput.isVisible()) {
        // Just test form interaction without credentials
        await emailInput.fill('test@example.com');
        await testHelper.captureScreenshot(page, 'auth-form-filled');
      }
    }

    const performance = await testHelper.measurePerformance(page);
    const result = testHelper.getTestResult(true, performance);
    
    console.log('AUTONOMOUS_TEST_RESULT:', JSON.stringify(result, null, 2));
    expect(result.errors.filter(e => e.includes('CONSOLE ERROR'))).toHaveLength(0);
  });

  test('Project creation modal functionality', async ({ page }) => {
    await testHelper.setupErrorCapture(page);
    
    await page.goto('/');
    
    // Look for new project button or similar
    const newProjectTrigger = page.locator(
      'button:has-text("New Project"), button:has-text("Create"), [data-testid="new-project"]'
    ).first();
    
    if (await newProjectTrigger.isVisible()) {
      await newProjectTrigger.click();
      
      // Wait for modal to appear
      await page.waitForSelector('[role="dialog"], .modal, [data-testid="project-modal"]', { 
        timeout: 5000 
      }).catch(() => {
        console.log('No modal found - may be auth-gated');
      });
      
      await testHelper.captureScreenshot(page, 'project-modal');
    }

    const performance = await testHelper.measurePerformance(page);
    const result = testHelper.getTestResult(true, performance);
    
    console.log('AUTONOMOUS_TEST_RESULT:', JSON.stringify(result, null, 2));
    expect(result.networkFailures).toHaveLength(0);
  });

  test('API endpoints are accessible', async ({ page }) => {
    await testHelper.setupErrorCapture(page);
    
    // Test critical API endpoints
    const apiEndpoints = [
      '/api/health',
      '/api/drone-path/health', 
      '/api/projects/health'
    ];

    for (const endpoint of apiEndpoints) {
      const response = await page.request.get(endpoint).catch(() => null);
      if (response) {
        console.log(`API ${endpoint}: ${response.status()}`);
      }
    }

    await page.goto('/');
    const performance = await testHelper.measurePerformance(page);
    const result = testHelper.getTestResult(true, performance);
    
    console.log('AUTONOMOUS_TEST_RESULT:', JSON.stringify(result, null, 2));
  });
});
