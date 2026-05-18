import { test, expect, Page } from '@playwright/test';

async function dismissElicitationIfPresent(page: Page) {
  try {
    await page.getByRole('button', { name: 'Fortsett med Gemini' }).click({ timeout: 3000 });
  } catch {
    // modal not present, continue
  }
}

const QUERY =
  'will china invade taiwan? focus on state sponsoresd cyber groups and attacks against electrical infrastructure. use next 6 months as timeline. include pacific states reactions';


test.describe('Direction Phase', () => {
  test('user completes direction phase and reaches collection plan', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('textbox', { name: 'Type anything...' }).click();
    await page.getByRole('textbox', { name: 'Type anything...' }).fill('Focus on');
    await page.getByRole('textbox', { name: 'Type anything...' }).press('ControlOrMeta+a');
    await page.getByRole('textbox', { name: 'Type anything...' }).fill(QUERY);
    await page.getByRole('button', { name: '🇨🇳 China' }).click();
    await page.getByRole('button', { name: '🌐 Global' }).click();
    await page.getByRole('button', { name: 'Send message' }).click();
    await page.getByRole('button', { name: 'Approve & Continue' }).click();
    await page.getByRole('button', { name: 'Fortsett med Gemini' }).click();
    await page.getByText('Show reasoning').click();
    await page.getByRole('button', { name: 'Approve & Continue' }).click();

    await expect(page.getByRole('heading', { name: 'Collection Plan' })).toBeVisible({ timeout: 60_000 });
  });
});


test.describe('Collection Phase', () => {
  test('user approves plan, selects sources and sees collection results', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('textbox', { name: 'Type anything...' }).click();
    await page.getByRole('textbox', { name: 'Type anything...' }).fill('Focus on');
    await page.getByRole('textbox', { name: 'Type anything...' }).press('ControlOrMeta+a');
    await page.getByRole('textbox', { name: 'Type anything...' }).fill(QUERY);
    await page.getByRole('button', { name: '🇨🇳 China' }).click();
    await page.getByRole('button', { name: '🌐 Global' }).click();
    await page.getByRole('button', { name: 'Send message' }).click();
    await page.getByRole('button', { name: 'Approve & Continue' }).click();
    await page.getByRole('button', { name: 'Fortsett med Gemini' }).click();
    await page.getByText('Show reasoning').click();
    await page.getByRole('button', { name: 'Approve & Continue' }).click();

    await page.getByRole('button', { name: 'Upload Files' }).click();
    await page.getByRole('button', { name: 'close' }).first().click();
    await page.getByRole('button', { name: 'Approve & Continue' }).click();
    await page.getByRole('button', { name: 'AlienVault OTX Open threat' }).click();
    await page.getByRole('button', { name: 'AlienVault OTX Open threat' }).click();
    await page.getByRole('button', { name: 'Web Search Searching the web' }).click();
    await page.getByRole('button', { name: 'Uploaded Documents PDFs,' }).click();
    await page.getByRole('button', { name: 'AlienVault OTX Open threat' }).click();
    await page.getByRole('button', { name: 'Start Collecting' }).click();
    await dismissElicitationIfPresent(page);
    await page.getByRole('button', { name: 'View Raw Data →' }).click({ timeout: 120_000 });
    await page.getByText('Knowledge Bank3 items').click();
    await page.getByRole('button', { name: 'close' }).first().click();
    await page.getByRole('button', { name: 'Accept' }).click();
    await dismissElicitationIfPresent(page);

    await expect(page.getByRole('cell', { name: 'F-01' })).toBeVisible({ timeout: 60_000 });
  });
});


test.describe('Processing Phase', () => {
  test('user reviews findings and accepts processing results', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('textbox', { name: 'Type anything...' }).click();
    await page.getByRole('textbox', { name: 'Type anything...' }).fill('Focus on');
    await page.getByRole('textbox', { name: 'Type anything...' }).press('ControlOrMeta+a');
    await page.getByRole('textbox', { name: 'Type anything...' }).fill(QUERY);
    await page.getByRole('button', { name: '🇨🇳 China' }).click();
    await page.getByRole('button', { name: '🌐 Global' }).click();
    await page.getByRole('button', { name: 'Send message' }).click();
    await page.getByRole('button', { name: 'Approve & Continue' }).click();
    await page.getByRole('button', { name: 'Fortsett med Gemini' }).click();
    await page.getByText('Show reasoning').click();
    await page.getByRole('button', { name: 'Approve & Continue' }).click();

    await page.getByRole('button', { name: 'Upload Files' }).click();
    await page.getByRole('button', { name: 'close' }).first().click();
    await page.getByRole('button', { name: 'Approve & Continue' }).click();
    await page.getByRole('button', { name: 'AlienVault OTX Open threat' }).click();
    await page.getByRole('button', { name: 'AlienVault OTX Open threat' }).click();
    await page.getByRole('button', { name: 'Web Search Searching the web' }).click();
    await page.getByRole('button', { name: 'Uploaded Documents PDFs,' }).click();
    await page.getByRole('button', { name: 'AlienVault OTX Open threat' }).click();
    await page.getByRole('button', { name: 'Start Collecting' }).click();
    await dismissElicitationIfPresent(page);
    await page.getByRole('button', { name: 'View Raw Data →' }).click({ timeout: 120_000 });
    await page.getByText('Knowledge Bank3 items').click();
    await page.getByRole('button', { name: 'close' }).first().click();
    await page.getByRole('button', { name: 'Accept' }).click();
    await dismissElicitationIfPresent(page);

    await page.getByRole('cell', { name: 'F-01' }).click({ timeout: 60_000 });
    await page.getByRole('button', { name: 'close' }).first().click();
    await page.getByRole('button', { name: 'Accept' }).click();
    await dismissElicitationIfPresent(page);

    await expect(page.getByRole('button', { name: 'Download PDF' })).toBeVisible({ timeout: 60_000 });
  });
});


test.describe('Analysis and Council Phase', () => {
  test('user downloads PDF, runs council and sees advisory note', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('textbox', { name: 'Type anything...' }).click();
    await page.getByRole('textbox', { name: 'Type anything...' }).fill('Focus on');
    await page.getByRole('textbox', { name: 'Type anything...' }).press('ControlOrMeta+a');
    await page.getByRole('textbox', { name: 'Type anything...' }).fill(QUERY);
    await page.getByRole('button', { name: '🇨🇳 China' }).click();
    await page.getByRole('button', { name: '🌐 Global' }).click();
    await page.getByRole('button', { name: 'Send message' }).click();
    await page.getByRole('button', { name: 'Approve & Continue' }).click();
    await page.getByRole('button', { name: 'Fortsett med Gemini' }).click();
    await page.getByText('Show reasoning').click();
    await page.getByRole('button', { name: 'Approve & Continue' }).click();

    await page.getByRole('button', { name: 'Upload Files' }).click();
    await page.getByRole('button', { name: 'close' }).first().click();
    await page.getByRole('button', { name: 'Approve & Continue' }).click();
    await page.getByRole('button', { name: 'AlienVault OTX Open threat' }).click();
    await page.getByRole('button', { name: 'AlienVault OTX Open threat' }).click();
    await page.getByRole('button', { name: 'Web Search Searching the web' }).click();
    await page.getByRole('button', { name: 'Uploaded Documents PDFs,' }).click();
    await page.getByRole('button', { name: 'AlienVault OTX Open threat' }).click();
    await page.getByRole('button', { name: 'Start Collecting' }).click();
    await dismissElicitationIfPresent(page);
    await page.getByRole('button', { name: 'View Raw Data →' }).click({ timeout: 120_000 });
    await page.getByText('Knowledge Bank3 items').click();
    await page.getByRole('button', { name: 'close' }).first().click();
    await page.getByRole('button', { name: 'Accept' }).click();
    await dismissElicitationIfPresent(page);

    await page.getByRole('cell', { name: 'F-01' }).click({ timeout: 60_000 });
    await page.getByRole('button', { name: 'close' }).first().click();
    await page.getByRole('button', { name: 'Accept' }).click();
    await dismissElicitationIfPresent(page);

    const downloadPromise = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Download PDF' }).click({ timeout: 60_000 });
    await downloadPromise;
    await page.getByRole('heading', { name: 'Framing by Perspective' }).click();
    await page.getByRole('button', { name: 'Go to Council' }).click();
    await page.getByRole('button', { name: 'Select all' }).click();
    await page.getByRole('button', { name: 'Run council' }).click();

    await expect(page.getByRole('heading', { name: 'Advisory note' })).toBeVisible({ timeout: 60_000 });
  });
});
