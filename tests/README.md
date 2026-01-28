# E2E Testing

This directory contains end-to-end tests for the MCP Project using Playwright.

## Running Tests

From the project root:

```bash
# Run all E2E tests (headless)
npm run test:e2e

# Run tests with UI mode (interactive)
npm run test:e2e:ui

# Run tests in headed mode (see browser)
npm run test:e2e:headed

# View test report after running tests
npm run test:e2e:report
```

## Test Structure

```
tests/
└── e2e/
    └── app.spec.ts    # Application E2E tests
```

## Configuration

- **Config file**: `playwright.config.ts` at project root
- **Base URL**: http://localhost:5173 (Vite dev server)
- **Browsers**: Chromium, Firefox, WebKit
- **Auto-start**: Dev server starts automatically when running tests

## Adding New Tests

Create new `.spec.ts` files in the `tests/e2e/` directory:

```typescript
import { test, expect } from '@playwright/test';

test.describe('Feature Name', () => {
  test('should do something', async ({ page }) => {
    await page.goto('/some-route');

    // Your test assertions
    await expect(page.getByRole('button')).toBeVisible();
  });
});
```

## Best Practices

- Test user flows, not implementation details
- Use semantic locators (getByRole, getByLabel, etc.)
- Keep tests independent and isolated
- Use descriptive test names
