import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { readFileSync } from 'fs'
import { resolve } from 'path'

const GOAL = 70

function printCoverageSummary(metrics: [string, number][]) {
  const LINE = '─'.repeat(54)
  const lines = [
    `\n${LINE}`,
    `  Coverage Summary  (goal: ${GOAL}%)`,
    LINE,
  ]
  let allPassed = true
  for (const [name, pct] of metrics) {
    const passed = pct >= GOAL
    if (!passed) allPassed = false
    const label  = name.padEnd(12)
    const value  = `${pct}%`.padEnd(8)
    const status = passed ? '✓ PASSED' : '✗ FAILED'
    lines.push(`  ${label}  ${value}  goal: ${GOAL}%   ${status}`)
  }
  lines.push(LINE)
  lines.push(allPassed
    ? '  Overall: all thresholds met ✓'
    : '  Overall: some thresholds not met ✗')
  lines.push(`${LINE}\n`)
  process.stdout.write(lines.join('\n') + '\n')
}

const coverageSummaryReporter = {
  onCoverage(coverage: unknown) {
    try {
      // Vitest passes an Istanbul CoverageMap — try getCoverageSummary() first
      const map = coverage as { getCoverageSummary?: () => { statements: {pct: number}, branches: {pct: number}, functions: {pct: number}, lines: {pct: number} } }
      const summary = typeof map?.getCoverageSummary === 'function' ? map.getCoverageSummary() : null

      if (summary?.statements?.pct !== undefined) {
        printCoverageSummary([
          ['Statements', summary.statements.pct],
          ['Branches',   summary.branches.pct],
          ['Functions',  summary.functions.pct],
          ['Lines',      summary.lines.pct],
        ])
        return
      }

      // Fallback: read json-summary written by the 'json-summary' reporter
      const summaryPath = resolve(process.cwd(), 'coverage/coverage-summary.json')
      const { total: t } = JSON.parse(readFileSync(summaryPath, 'utf-8'))
      printCoverageSummary([
        ['Statements', t.statements.pct],
        ['Branches',   t.branches.pct],
        ['Functions',  t.functions.pct],
        ['Lines',      t.lines.pct],
      ])
    } catch {
      // not running with --coverage, or file not yet available
    }
  },
}

export default defineConfig({
  plugins: [react()],
  test: {
    typecheck: {
      tsconfig: "./tsconfig.test.json",
    },
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    reporters: ['default', coverageSummaryReporter],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'json-summary', 'html'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/dist/**',
      ],
      thresholds: {
        lines: 70,
        functions: 70,
        branches: 70,
        statements: 70,
      },
    },
  },
})
