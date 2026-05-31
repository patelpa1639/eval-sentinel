// Mock mode — a static fixture of the /api/state response and the /api/run
// SSE event stream, so the UI can be developed + visually verified WITHOUT the
// backend running (the real run takes ~2 min).
//
// Toggle: set VITE_MOCK=1 (e.g. `VITE_MOCK=1 npm run dev`) OR append ?mock=1
// to the URL. See README.

import type { SentinelEvent, StateResponse, ApproveResponse } from './types';

export const MOCK_STATE: StateResponse = {
  dataset: 'smart-home-commands',
  baseline: {
    overall: 100,
    per_category: { lights: 100, climate: 100, media: 100, security: 100, other: 100 },
  },
  current: {
    overall: 84,
    per_category: { lights: 100, climate: 100, media: 60, security: 60, other: 100 },
  },
  regressed_categories: ['media', 'security'],
  phoenix_url: 'https://app.phoenix.arize.com/projects/smart-home-commands',
};

// The streamed incident. Ordered exactly as a real run would emit them.
export const MOCK_EVENTS: SentinelEvent[] = [
  {
    type: 'plan',
    text:
      'Overall accuracy dropped on smart-home-commands. I will detect which categories regressed, root-cause the failures, propose a corrected routing prompt, re-evaluate to verify, and report — holding at an approval gate before promoting anything.',
  },
  { type: 'phase', phase: 'detect', label: 'Detecting regression' },
  {
    type: 'tool_call',
    name: 'phoenix.get_experiment_comparison',
    args: { dataset: 'smart-home-commands', baseline: 'exp_baseline', current: 'exp_current' },
  },
  {
    type: 'tool_result',
    name: 'phoenix.get_experiment_comparison',
    kind: 'regression',
    data: {
      overall: { baseline: 100, current: 84 },
      rows: [
        { category: 'lights', baseline: 100, current: 100 },
        { category: 'climate', baseline: 100, current: 100 },
        { category: 'media', baseline: 100, current: 60 },
        { category: 'security', baseline: 100, current: 60 },
        { category: 'other', baseline: 100, current: 100 },
      ],
    },
  },
  {
    type: 'narration',
    text:
      'Overall fell **100% → 84%** (−16). Two categories regressed: **media** and **security**, both to 60%. lights, climate and other are unaffected — this is a *targeted* failure, not noise.',
  },
  { type: 'phase', phase: 'root_cause', label: 'Root-causing failures' },
  {
    type: 'tool_call',
    name: 'phoenix.get_failing_examples',
    args: { categories: ['media', 'security'] },
  },
  {
    type: 'tool_result',
    name: 'phoenix.get_failing_examples',
    kind: 'failures',
    data: {
      rows: [
        {
          command: 'turn up the volume in the office',
          expected: 'media',
          predicted: 'other',
        },
        {
          command: 'play the news on the bedroom speaker',
          expected: 'media',
          predicted: 'other',
        },
        {
          command: 'show me the backyard camera',
          expected: 'security',
          predicted: 'other',
        },
        {
          command: 'did the garage door close?',
          expected: 'security',
          predicted: 'other',
        },
      ],
    },
  },
  {
    type: 'narration',
    text:
      'Every failing example collapses into **other**. The current routing prompt lost its description of what belongs in *media* (audio/volume/playback) and *security* (cameras, doors, locks), so ambiguous phrasing falls through to the catch-all.',
  },
  { type: 'phase', phase: 'propose', label: 'Proposing fix' },
  {
    type: 'proposed_prompt',
    text: `You are a smart-home command router. Classify each command into exactly one category:
- lights: lamps, brightness, dimming, light scenes
- climate: thermostat, temperature, heating, cooling, fans
- media: audio, volume, music, news, playback on any speaker
- security: cameras, door/garage state, locks, alarms, motion
- other: anything that does not clearly fit the above

Return only the category name.`,
  },
  {
    type: 'narration',
    text:
      'Proposed prompt restores explicit **media** and **security** descriptions, including the volume/speaker and camera/garage phrasings that were mis-routing.',
  },
  { type: 'phase', phase: 'verify', label: 'Verifying fix' },
  {
    type: 'tool_call',
    name: 'phoenix.run_experiment',
    args: { prompt: 'proposed', dataset: 'smart-home-commands' },
  },
  {
    type: 'tool_result',
    name: 'phoenix.run_experiment',
    kind: 'recovery',
    data: {
      overall: { current: 84, healed: 100 },
      rows: [
        { category: 'lights', current: 100, healed: 100 },
        { category: 'climate', current: 100, healed: 100 },
        { category: 'media', current: 60, healed: 100 },
        { category: 'security', current: 60, healed: 100 },
        { category: 'other', current: 100, healed: 100 },
      ],
    },
  },
  {
    type: 'narration',
    text:
      'Re-evaluation on the full dataset: **media 60% → 100%**, **security 60% → 100%**, overall back to **100%**. No regressions introduced elsewhere.',
  },
  { type: 'phase', phase: 'approval', label: 'Awaiting approval' },
  {
    type: 'approval_gate',
    proposed_prompt: `You are a smart-home command router. Classify each command into exactly one category:
- lights: lamps, brightness, dimming, light scenes
- climate: thermostat, temperature, heating, cooling, fans
- media: audio, volume, music, news, playback on any speaker
- security: cameras, door/garage state, locks, alarms, motion
- other: anything that does not clearly fit the above

Return only the category name.`,
    new_experiment_id: 'exp_healed_8f21c',
  },
  { type: 'phase', phase: 'report', label: 'Postmortem' },
  {
    type: 'report',
    text: `### Incident postmortem — smart-home-commands

**Impact** · Overall routing accuracy fell 100% → 84% (−16). Two of five categories regressed.

**Root cause** · The routing prompt dropped the descriptions for *media* and *security*, so volume/playback and camera/door commands fell through to *other*.

**Fix** · Restored explicit category descriptions covering the mis-routed phrasings.

**Verification** · Full re-evaluation: media 60→100, security 60→100, overall 84→100. No new regressions.

**Status** · Fix verified, held at approval gate \`exp_healed_8f21c\` pending human promotion.`,
  },
  { type: 'done' },
];

// --- Mock-only dashboard enrichment (no backend equivalent) -----------------
// Used to populate the KPI tiles and the "Accuracy over runs" trend chart in
// mock mode. In live mode the chart is built honestly from /api/state only.

export interface TrendPoint {
  run: number;
  label: string;
  accuracy: number;
  marker?: 'dip' | 'recovery';
}

// A plausible run history: a long healthy stretch, the regression dip at run 11
// (84), and the verified recovery at run 12 (100).
export const MOCK_TREND: TrendPoint[] = [
  { run: 1, label: 'run 1', accuracy: 100 },
  { run: 2, label: 'run 2', accuracy: 100 },
  { run: 3, label: 'run 3', accuracy: 98 },
  { run: 4, label: 'run 4', accuracy: 100 },
  { run: 5, label: 'run 5', accuracy: 100 },
  { run: 6, label: 'run 6', accuracy: 99 },
  { run: 7, label: 'run 7', accuracy: 100 },
  { run: 8, label: 'run 8', accuracy: 100 },
  { run: 9, label: 'run 9', accuracy: 100 },
  { run: 10, label: 'run 10', accuracy: 100 },
  { run: 11, label: 'run 11', accuracy: 84, marker: 'dip' },
  { run: 12, label: 'run 12', accuracy: 100, marker: 'recovery' },
];

export const MOCK_METRICS = {
  evalRuns: 12,
  meanTimeToHeal: '1m 48s',
  // tiny sparkline series for each KPI tile
  spark: {
    accuracy: [100, 100, 98, 100, 100, 99, 100, 100, 100, 100, 84, 100],
    regressed: [0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 2, 0],
    runs: [4, 5, 6, 6, 7, 8, 9, 10, 10, 11, 11, 12],
    heal: [132, 128, 140, 121, 118, 124, 116, 120, 109, 114, 112, 108],
  },
};

export const MOCK_APPROVE: Record<'approve' | 'reject', ApproveResponse> = {
  approve: {
    ok: true,
    promoted: true,
    message: 'Promoted exp_healed_8f21c to production. Routing prompt updated.',
  },
  reject: {
    ok: true,
    promoted: false,
    message: 'Proposed fix rejected. Production prompt unchanged.',
  },
};
