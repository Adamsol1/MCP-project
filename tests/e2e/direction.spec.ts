import { test } from '@playwright/test';

test.setTimeout(600_000);

test('direction phase', async ({ page }) => {
  await page.goto('http://localhost:5173/');
  await page.getByRole('textbox', { name: 'Type anything...' }).click();
  await page.getByRole('textbox', { name: 'Type anything...' }).fill('will china invadte taiwan? focus on state sponsored cyber groups and attacks against electrical infrastructure. Focus on potetnail impact and pacific state reactions. set timeframe to the next 6 months');
  await page.getByRole('button', { name: '🇨🇳 China' }).click();
  await page.getByRole('button', { name: '🇪🇺 EU' }).click();
  await page.getByRole('button', { name: 'Send message' }).click();
  await page.getByRole('button', { name: 'Approve & Continue' }).click();
  await page.getByRole('button', { name: 'Fortsett med Gemini' }).click();
  await page.getByRole('button', { name: 'Approve & Continue' }).click();
});
