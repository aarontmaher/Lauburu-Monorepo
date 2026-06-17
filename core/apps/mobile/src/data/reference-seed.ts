/**
 * Reference seed — canonical sections + canonical positions from the
 * Lauburu Grappling Map schema (locked decisions in CLAUDE.md).
 *
 * This is a first-slice bundled preview so the mobile app has a real
 * knowledge/reference entry point without blocking on full OPML sync.
 * It contains ONLY structural canonical names from the locked schema
 * (sections, positions, headings). NO invented technique names and NO
 * invented content — that's Aaron's domain and flows through the OPML
 * pipeline on the website.
 *
 * Shape is intentionally close to the future full catalogue so that
 * switching from this seed to a live OPML-backed feed later is a drop-in
 * replacement: `ReferencePosition` is the stable contract.
 */

/** The 6 headings used across most sections (Wrestling uses "Defence"). */
export const STANDARD_HEADINGS = [
  'Setups/Entries',
  'Control',
  'Offence',
  'Defence/Escapes',
  'Submissions',
  'Offensive transitions',
] as const;

/** Wrestling uses a slightly different spelling. */
export const WRESTLING_HEADINGS = [
  'Setups/Entries',
  'Control',
  'Offence',
  'Defence',
  'Submissions',
  'Offensive transitions',
] as const;

/** Hand Fighting is the only section without Submissions. */
export const HAND_FIGHTING_HEADINGS = [
  'Setups/Entries',
  'Control',
  'Offence',
  'Defence',
  'Offensive transitions',
] as const;

export interface ReferencePosition {
  /** Stable canonical name — matches the schema in CLAUDE.md exactly. */
  name: string;
  /** Perspectives pair for this position (e.g. Attacker / Defender). */
  perspectives: [string, string];
  /** Section-level headings that apply to this position. */
  headings: readonly string[];
  /**
   * Whether this position is considered "built out" on the website.
   * Mirrors the current CURRENT SNAPSHOT in CLAUDE.md.
   */
  built_out?: boolean;
}

export interface ReferenceSection {
  id: string;
  label: string;
  description: string;
  perspectives: [string, string];
  positions: ReferencePosition[];
}

/**
 * Built-out set lifted from CLAUDE.md CURRENT SNAPSHOT (as of 2026-04-07):
 * J point, K guard, Quarter guard, Supine Guard, Mount, Turtle,
 * Berimbolo, Grounded 50/50, Wrestling bodylock, Back Control, Crab ride.
 */
const BUILT_OUT = new Set<string>([
  'J point',
  'K guard',
  'Quarter guard',
  'Supine Guard',
  'Mount',
  'Turtle',
  'Berimbolo',
  'Grounded 50/50',
  'Wrestling bodylock',
  'Back Control',
  'Crab ride',
]);

function dp(name: string): ReferencePosition {
  return {
    name,
    perspectives: ['Attacker', 'Defender'],
    headings: STANDARD_HEADINGS,
    built_out: BUILT_OUT.has(name),
  };
}

function guard(name: string): ReferencePosition {
  return {
    name,
    perspectives: ['Passer', 'Guard player'],
    headings: STANDARD_HEADINGS,
    built_out: BUILT_OUT.has(name),
  };
}

function scr(name: string): ReferencePosition {
  return {
    name,
    perspectives: ['Initiative', 'Defensive'],
    headings: STANDARD_HEADINGS,
    built_out: BUILT_OUT.has(name),
  };
}

function wr(name: string): ReferencePosition {
  return {
    name,
    perspectives: ['Attacker', 'Defender'],
    headings: WRESTLING_HEADINGS,
    built_out: BUILT_OUT.has(name),
  };
}

export const REFERENCE_SECTIONS: ReferenceSection[] = [
  {
    id: 'dominant_positions',
    label: 'Dominant Positions',
    description: 'Top positions with a clear attacker and defender.',
    perspectives: ['Attacker', 'Defender'],
    positions: [
      dp('Turtle'),
      dp('Front Headlock'),
      dp('Mount'),
      dp('Side Control'),
      dp('North South'),
      dp('Back Control'),
    ],
  },
  {
    id: 'guard',
    label: 'Guard',
    description: '19 canonical no-gi guard positions.',
    perspectives: ['Passer', 'Guard player'],
    positions: [
      guard('Shin pin'),
      guard('Supine Guard'),
      guard('J point'),
      guard('Closed Guard'),
      guard('Headquarters'),
      guard('Quarter guard'),
      guard('Half Guard Passing'),
      guard('Butterfly guard'),
      guard('Half butterfly'),
      guard('Knee shield half guard'),
      guard('K guard'),
      guard('De la riva'),
      guard('Reverse de la riva'),
      guard('Butterfly ashi'),
      guard('Outside ashi'),
      guard('X guard'),
      guard('Single leg X'),
      guard('Seated Guard'),
      guard('Half guard'),
    ],
  },
  {
    id: 'scrambles',
    label: 'Scrambles',
    description: 'Transitional positions with initiative vs defensive perspectives.',
    perspectives: ['Initiative', 'Defensive'],
    positions: [scr('Berimbolo'), scr('Crab ride'), scr('Grounded 50/50')],
  },
  {
    id: 'wrestling',
    label: 'Wrestling',
    description: 'Takedowns and bodylock positions from no-gi wrestling.',
    perspectives: ['Attacker', 'Defender'],
    positions: [
      wr('Head inside single leg'),
      wr('Head outside single leg'),
      wr('Double leg'),
      wr('Low ankle'),
      wr('Wrestling bodylock'),
      wr('Side bodylock'),
      wr('Wrestling rear bodylock'),
    ],
  },
  {
    id: 'hand_fighting',
    label: 'Hand Fighting',
    description: 'Grip and tie positions. No submissions heading.',
    perspectives: ['You', 'Opponent'],
    positions: [
      {
        name: 'Outside tie',
        perspectives: ['You', 'Opponent'],
        headings: HAND_FIGHTING_HEADINGS,
      },
      {
        name: 'Inside tie',
        perspectives: ['You', 'Opponent'],
        headings: HAND_FIGHTING_HEADINGS,
      },
      {
        name: 'Collar tie',
        perspectives: ['You', 'Opponent'],
        headings: HAND_FIGHTING_HEADINGS,
      },
      {
        name: 'Underhook',
        perspectives: ['You', 'Opponent'],
        headings: HAND_FIGHTING_HEADINGS,
      },
      {
        name: 'Overhook',
        perspectives: ['You', 'Opponent'],
        headings: HAND_FIGHTING_HEADINGS,
      },
      {
        name: '2-on-1',
        perspectives: ['You', 'Opponent'],
        headings: HAND_FIGHTING_HEADINGS,
      },
      {
        name: 'Over/Under',
        perspectives: ['You', 'Opponent'],
        headings: HAND_FIGHTING_HEADINGS,
      },
    ],
  },
];

export const REFERENCE_TOTAL_POSITIONS = REFERENCE_SECTIONS.reduce(
  (acc, s) => acc + s.positions.length,
  0,
);

export const REFERENCE_BUILT_OUT_COUNT = REFERENCE_SECTIONS.reduce(
  (acc, s) => acc + s.positions.filter((p) => p.built_out).length,
  0,
);
