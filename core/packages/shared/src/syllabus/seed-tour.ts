/**
 * Legacy export kept for backend/mobile compatibility.
 * `SEED_TOUR` now mirrors the single global AppTour content.
 */

import type { AppTourContent } from './tour-content.types';

export const SEED_TOUR: AppTourContent = {
  schemaVersion: 1,
  updatedAt: '2026-04-15',
  steps: [
    {
      id: 'tour-welcome',
      title: 'Welcome to Lauburu',
      body: 'Your grappling intelligence hub. This quick tour shows you what each section does.',
      detail: null,
      surface: 'general',
    },
    {
      id: 'tour-home',
      title: 'Home',
      body: "Today's recovery snapshot, training guidance, and AI Coach insights all live here.",
      detail: 'Recovery data comes from WHOOP when connected. Seed data stays visible until a live sync completes.',
      surface: 'home',
    },
    {
      id: 'tour-ai-coach',
      title: 'AI Coach',
      body: 'Tap the floating coach button from any screen to ask about training, recovery, nutrition, or HIIT.',
      detail: 'Answers use your real app data and tell you when data is missing or stale rather than guessing.',
      surface: 'coach',
    },
    {
      id: 'tour-health',
      title: 'Health Sources',
      body: 'WHOOP, Apple Health, and Cronometer are tracked independently with their real connection status.',
      detail: 'WHOOP provides recovery, HRV, and strain. Apple Health provides sleep and steps. Cronometer is not yet connected because there is no public API.',
      surface: 'health',
    },
    {
      id: 'tour-nutrition',
      title: 'Nutrition',
      body: 'Log meals via manual entry, barcode scan, or AI photo estimate. Only confirmed entries count.',
      detail: 'Barcode scans use Open Food Facts. AI photo estimates require your review before they enter totals.',
      surface: 'nutrition',
    },
    {
      id: 'tour-train',
      title: 'Train',
      body: 'Log grappling sessions, conditioning, HIIT intervals, and steady-state cardio.',
      detail: 'Training logs stay in the app so Coach can use your recent work without repeated live pulls.',
      surface: 'train',
    },
    {
      id: 'tour-hiit',
      title: 'HIIT Progress',
      body: 'Review recent HIIT sessions and compare set-by-set changes over time.',
      detail: 'Machine adapters are not yet live. Manual entry still captures the essentials without faking live watts or HR.',
      surface: 'hiit',
    },
    {
      id: 'tour-map',
      title: '3D Map',
      body: 'The interactive 3D mind map shows every position and how they connect.',
      detail: 'Tap nodes to explore move chains, then jump into Reference or Syllabus when you need more detail.',
      surface: 'map',
    },
    {
      id: 'tour-filters',
      title: 'Filters',
      body: 'Use filters to switch between All, My Game, Learned, and Drilling views on the map.',
      detail: 'Filters help you focus on the part of the graph that matches your current training goal.',
      surface: 'filters',
    },
    {
      id: 'tour-syllabus',
      title: 'Belt Syllabus',
      body: 'Your belt roadmap ties requirements to real positions and techniques in the app.',
      detail: 'Progress updates as you mark techniques as drilling or learned.',
      surface: 'syllabus',
    },
    {
      id: 'tour-reference',
      title: 'Reference',
      body: 'Reference is the full technique tree: positions, roles, headings, and techniques.',
      detail: 'Use it to build your game map and review canonical technique breakdowns.',
      surface: 'reference',
    },
    {
      id: 'tour-settings',
      title: 'Settings',
      body: 'Configure coaching preferences, data consent, and subscription details here.',
      detail: 'You can replay this full app tour from Settings any time.',
      surface: 'settings',
    },
  ],
};
