import { test } from '@playwright/test';

test.setTimeout(600_000);

test('council phase', async ({ page }) => {
  await page.goto('http://localhost:5173/');
  await page.getByRole('textbox', { name: 'Type anything...' }).click();
  await page.getByRole('textbox', { name: 'Type anything...' }).fill('will china invadte taiwan? focus on state sponsored cyber groups and attacks against electrical infrastructure. Focus on potetnail impact and pacific state reactions. set timeframe to the next 6 months');
  await page.getByRole('button', { name: '🇨🇳 China' }).click();
  await page.getByRole('button', { name: '🇪🇺 EU' }).click();
  await page.getByRole('button', { name: 'Send message' }).click();
  await page.getByRole('button', { name: 'Approve & Continue' }).click();
  await page.getByRole('button', { name: 'Fortsett med Gemini' }).click();
  await page.getByRole('button', { name: 'Approve & Continue' }).click();
  // COLLECTION
  await page.getByRole('button', { name: 'Approve & Continue' }).click();
  await page.getByRole('button', { name: 'AlienVault OTX Open threat' }).click();
  await page.getByRole('button', { name: 'Uploaded Documents PDFs,' }).click();
  await page.getByRole('button', { name: 'Start Collecting' }).click();
  await page.getByRole('button', { name: 'Fortsett med Gemini' }).click();
  await page.getByRole('button', { name: 'Accept' }).click();
  // PROCESSING
  await page.getByRole('button', { name: 'political' }).click();
  await page.getByRole('button', { name: 'Accept' }).click();
  // ANALYSIS
  await page.getByRole('button', { name: 'Go to Council' }).click();
  // COUNCIL
  await page.getByRole('button', { name: 'F-01 PLA Cyber Access Taiwan' }).click();
  await page.getByRole('button', { name: 'Run council' }).click();
});
