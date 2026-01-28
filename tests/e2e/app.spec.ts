import { test, expect } from '@playwright/test';

test.describe('MCP Project', () => {
  test('homepage loads successfully', async ({ page }) => {
    await page.goto('/');

    // Check that the main heading is visible
    await expect(page.getByRole('heading', { name: 'MCP Project' })).toBeVisible();

    // Check that the subtitle is present
    await expect(page.getByText('Ready to start building')).toBeVisible();
  });

  test('has correct page title', async ({ page }) => {
    await page.goto('/');

    await expect(page).toHaveTitle('MCP Project');
  });
});
