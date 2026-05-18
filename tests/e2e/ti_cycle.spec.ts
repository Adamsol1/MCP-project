import { test, expect, Page } from '@playwright/test';

// Happy-path E2E for the full TI cycle: Direction → Collection → Processing → Analysis → Council.
// AI/backend calls are mocked. Elicitation (TLP modal) is handled conditionally — it may or may
// not appear depending on AI response content, so dismissElicitationIfPresent() is called at each
// phase boundary where it is known to trigger.

const PLAN_WITH_SOURCES = JSON.stringify({
  plan: 'Collect from available intelligence sources.',
  steps: [
    {
      title: 'Knowledge Base',
      description: 'Query internal knowledge base.',
      suggested_sources: ['Knowledge Bank', 'AlienVault OTX'],
    },
  ],
  suggested_sources: ['Knowledge Bank', 'AlienVault OTX'],
});

const DIALOGUE_RESPONSES = [
  // 1. Initial message → PIRs
  {
    action: 'show_pir',
    question: 'Based on your input, here are the Priority Intelligence Requirements.',
  },
  // 2. Approve PIRs → collection plan (question must be JSON with suggested_sources)
  {
    action: 'show_plan',
    question: PLAN_WITH_SOURCES,
  },
  // 3. Approve plan → source selection
  {
    action: 'start_collecting',
    question: 'Ready to start collection. Select your sources and begin.',
  },
  // 4. Start Collecting → collection results
  {
    action: 'show_collection',
    question: 'Collection complete. Sources have been queried.',
  },
  // 5. Accept collection → processing results
  {
    action: 'show_processing',
    question: 'Processing complete. Findings have been extracted.',
  },
  // 6. Accept processing → analysis (question must be JSON AnalysisResponse)
  {
    action: 'show_analysis',
    question: JSON.stringify({
      data_source: 'session',
      latest_council_note: null,
      collection_coverage: null,
      processing_result: {
        findings: [
          {
            id: 'F-001',
            title: 'Volt Typhoon Pre-positioning',
            finding: 'Evidence of pre-positioning activity targeting Taiwanese electrical infrastructure.',
            evidence_summary: 'Network telemetry and OSINT corroborate staging activity.',
            source: 'osint',
            confidence: 82,
            relevant_to: ['PIR-1'],
            supporting_data: { attack_ids: ['T1078'] },
            why_it_matters: 'Suggests adversary access development ahead of potential action.',
            uncertainties: ['Attribution not fully confirmed.'],
            computed_confidence: null,
          },
        ],
        gaps: ['Attribution remains unresolved.'],
      },
      analysis_draft: {
        title: 'China–Taiwan Cyber Threat Assessment',
        summary: 'A likely state-directed pre-positioning campaign targeting critical infrastructure has been identified.',
        key_judgments: ['Volt Typhoon activity is consistent with PLA cyber doctrine.'],
        per_perspective_implications: {
          china: [
            {
              assertion: 'Operational pre-positioning aligns with strategic objectives.',
              supporting_finding_ids: ['F-001'],
              source_types: ['osint'],
              confidence: null,
            },
          ],
          eu: [
            {
              assertion: 'Critical infrastructure exposure warrants immediate attention.',
              supporting_finding_ids: ['F-001'],
              source_types: ['osint'],
              confidence: null,
            },
          ],
        },
        recommended_actions: ['Harden energy sector control systems immediately.'],
        information_gaps: ['Attribution remains unresolved.'],
      },
    }),
  },
];

const COUNCIL_RESPONSE = {
  status: 'complete',
  question: 'Assess the strongest evidence of Chinese state involvement.',
  participants: ['China Strategic Analyst', 'EU Policy Analyst'],
  rounds_completed: 2,
  summary: 'The council assessed with high confidence that Volt Typhoon activity represents deliberate strategic preparation.',
  key_agreements: ['Volt Typhoon is state-directed', 'Critical infrastructure is the primary target'],
  key_disagreements: ['Timing of potential action remains uncertain'],
  final_recommendation: 'Recommend immediate defensive hardening of energy sector control systems.',
  full_debate: [
    {
      round: 1,
      participant: 'China Strategic Analyst',
      response: 'The evidence is consistent with PLA cyber doctrine.',
      timestamp: '2026-05-01T10:00:00Z',
    },
  ],
  transcript_path: null,
};

// Clicks "Fortsett med Gemini" if the TLP elicitation modal is present, silently skips if not.
// Elicitation always appears after AI responses containing classified content, but is not
// guaranteed in every phase (e.g. processing), so this helper is used defensively.
async function dismissElicitationIfPresent(page: Page) {
  try {
    await page.getByRole('button', { name: 'Fortsett med Gemini' }).click({ timeout: 2000 });
  } catch {
    // modal not present, continue
  }
}

async function setupMocks(page: Page) {
  let callCount = 0;

  await page.route('**/api/dialogue/message', async (route) => {
    const response = DIALOGUE_RESPONSES[callCount] ?? DIALOGUE_RESPONSES[DIALOGUE_RESPONSES.length - 1];
    callCount++;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(response),
    });
  });

  await page.route('**/api/dialogue/collection-status/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'complete',
        current_source: null,
        current_activity: null,
        sources: {
          'Knowledge Bank': { call_count: 3, last_called_at: '2026-05-01T10:00:00Z' },
          'AlienVault OTX': { call_count: 2, last_called_at: '2026-05-01T10:00:01Z' },
        },
      }),
    });
  });

  await page.route('**/api/dialogue/elicitation/pending/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ pending_elicitation: null }),
    });
  });

  await page.route('**/api/dialogue/elicitation/**/respond', async (route) => {
    await route.fulfill({ status: 204 });
  });

  await page.route('**/api/analysis/council', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(COUNCIL_RESPONSE),
    });
  });

  await page.route('**/api/import/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'success', session_id: 'test-session', files: [] }),
    });
  });

  await page.route('**/api/sessions/**', async (route) => {
    await route.fulfill({ status: 204 });
  });
}

test.describe('Full TI Cycle – Happy Path', () => {
  test('completes full intelligence cycle from Direction to Council', async ({ page }) => {
    await setupMocks(page);
    await page.goto('/');

    // --- Direction: send initial query ---
    const input = page.getByRole('textbox', { name: 'Type anything...' });
    await input.fill(
      'Investigate whether China will invade Taiwan. Focus on cyber groups and state-sponsored groups targeting electrical infrastructure. Timeframe: next 6 months.'
    );
    await page.getByRole('button', { name: 'Send message' }).click();
    await dismissElicitationIfPresent(page);

    // --- PIR phase ---
    await expect(page.getByText('Priority Intelligence Requirements')).toBeVisible({ timeout: 10_000 });
    await page.getByRole('button', { name: 'Approve & Continue' }).click();
    await dismissElicitationIfPresent(page);

    // --- Collection Plan ---
    await expect(page.getByRole('heading', { name: 'Collection Plan' })).toBeVisible({ timeout: 10_000 });
    await page.getByRole('button', { name: 'Approve & Continue' }).click();

    // --- Source selection + Start Collecting ---
    await expect(page.getByRole('button', { name: 'Start Collecting' })).toBeEnabled({ timeout: 10_000 });
    await page.getByRole('button', { name: 'Start Collecting' }).click();
    await dismissElicitationIfPresent(page);

    // --- Collection results ---
    await page.getByRole('button', { name: 'Accept' }).click({ timeout: 15_000 });

    // --- Processing results (elicitation uncertain here) ---
    await dismissElicitationIfPresent(page);
    await page.getByRole('button', { name: 'Accept' }).click({ timeout: 10_000 });

    // --- Analysis ---
    await expect(page.getByText('Evidence Docket')).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('Go to Council')).toBeVisible();

    // --- Council ---
    await page.getByRole('button', { name: 'Go to Council' }).click();
    await page.getByRole('button', { name: 'Select all' }).click();
    await page.getByRole('button', { name: 'Run council' }).click();

    await expect(page.getByText('Council Note')).toBeVisible({ timeout: 10_000 });
  });
});
