#!/usr/bin/env node

/**
 * Autonomous Test Runner
 * Runs Playwright tests and returns structured results for the autonomous workflow
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

class AutonomousTestRunner {
  constructor(baseUrl, testPattern = 'autonomous-feedback-test.spec.ts') {
    this.baseUrl = baseUrl;
    this.testPattern = testPattern;
    this.resultsFile = path.join(__dirname, 'test-results.json');
  }

  async runTests() {
    console.log('🧪 Starting autonomous test suite...');
    console.log(`📍 Base URL: ${this.baseUrl}`);
    console.log(`🎯 Test pattern: ${this.testPattern}`);

    const startTime = Date.now();
    let results = {
      success: false,
      passed: 0,
      failed: 0,
      total: 0,
      duration: 0,
      errors: [],
      details: {},
      timestamp: new Date().toISOString(),
      baseUrl: this.baseUrl
    };

    try {
      // Set environment variables for Playwright
      process.env.PLAYWRIGHT_BASE_URL = this.baseUrl;
      
      // Run Playwright tests with JSON reporter
      const command = `npx playwright test tests/e2e/${this.testPattern} --reporter=json --output=test-results`;
      
      console.log(`🚀 Executing: ${command}`);
      
      const output = execSync(command, {
        cwd: process.cwd(),
        encoding: 'utf8',
        stdio: ['pipe', 'pipe', 'pipe']
      });

      // Parse JSON output
      const jsonResults = JSON.parse(output);
      
      results.total = jsonResults.stats?.expected || 0;
      results.passed = jsonResults.stats?.passed || 0;
      results.failed = jsonResults.stats?.failed || 0;
      results.duration = Date.now() - startTime;
      results.success = results.failed === 0 && results.total > 0;
      
      // Extract test details
      if (jsonResults.suites) {
        results.details = this.extractTestDetails(jsonResults.suites);
      }

      console.log('✅ Tests completed successfully');
      console.log(`📊 Results: ${results.passed}/${results.total} passed`);

    } catch (error) {
      results.duration = Date.now() - startTime;
      results.errors.push({
        type: 'execution_error',
        message: error.message,
        stderr: error.stderr?.toString() || '',
        stdout: error.stdout?.toString() || ''
      });

      // Try to parse partial results from stderr
      try {
        const errorOutput = error.stdout?.toString() || error.stderr?.toString() || '';
        if (errorOutput.includes('{') && errorOutput.includes('stats')) {
          const jsonMatch = errorOutput.match(/\{.*"stats".*\}/s);
          if (jsonMatch) {
            const partialResults = JSON.parse(jsonMatch[0]);
            results.total = partialResults.stats?.expected || 0;
            results.passed = partialResults.stats?.passed || 0;
            results.failed = partialResults.stats?.failed || 0;
          }
        }
      } catch (parseError) {
        console.warn('Could not parse partial results from error output');
      }

      console.error('❌ Test execution failed:', error.message);
    }

    // Save results to file
    fs.writeFileSync(this.resultsFile, JSON.stringify(results, null, 2));
    
    // Output structured results
    this.outputResults(results);
    
    return results;
  }

  extractTestDetails(suites) {
    const details = {};
    
    function processSuite(suite) {
      if (suite.specs) {
        suite.specs.forEach(spec => {
          const testName = spec.title;
          details[testName] = {
            status: spec.tests?.[0]?.results?.[0]?.status || 'unknown',
            duration: spec.tests?.[0]?.results?.[0]?.duration || 0,
            error: spec.tests?.[0]?.results?.[0]?.error?.message || null
          };
        });
      }
      
      if (suite.suites) {
        suite.suites.forEach(processSuite);
      }
    }
    
    suites.forEach(processSuite);
    return details;
  }

  outputResults(results) {
    console.log('\n' + '='.repeat(60));
    console.log('🎯 AUTONOMOUS TEST RESULTS');
    console.log('='.repeat(60));
    console.log(`📍 URL: ${results.baseUrl}`);
    console.log(`⏱️  Duration: ${results.duration}ms`);
    console.log(`📊 Tests: ${results.passed}/${results.total} passed`);
    console.log(`✅ Success: ${results.success}`);
    
    if (results.errors.length > 0) {
      console.log('\n❌ ERRORS:');
      results.errors.forEach((error, i) => {
        console.log(`${i + 1}. ${error.type}: ${error.message}`);
        if (error.stderr) {
          console.log(`   stderr: ${error.stderr.substring(0, 200)}...`);
        }
      });
    }
    
    if (Object.keys(results.details).length > 0) {
      console.log('\n📋 TEST DETAILS:');
      Object.entries(results.details).forEach(([test, detail]) => {
        const status = detail.status === 'passed' ? '✅' : '❌';
        console.log(`${status} ${test} (${detail.duration}ms)`);
        if (detail.error) {
          console.log(`   Error: ${detail.error}`);
        }
      });
    }
    
    console.log('='.repeat(60));
  }
}

// CLI usage
if (require.main === module) {
  const baseUrl = process.argv[2];
  const testPattern = process.argv[3] || 'autonomous-feedback-test.spec.ts';
  
  if (!baseUrl) {
    console.error('Usage: node autonomous-test-runner.js <base-url> [test-pattern]');
    console.error('Example: node autonomous-test-runner.js https://agent-123.example.com');
    process.exit(1);
  }
  
  const runner = new AutonomousTestRunner(baseUrl, testPattern);
  runner.runTests()
    .then(results => {
      process.exit(results.success ? 0 : 1);
    })
    .catch(error => {
      console.error('Fatal error:', error);
      process.exit(1);
    });
}

module.exports = AutonomousTestRunner;
