"use strict";
/**
 * Belt syllabus contracts — shared curriculum definitions that
 * the mobile app, map, and reference system can all consume.
 *
 * Architecture:
 *   - SyllabusBelt / SyllabusRequirement = SHARED curriculum definition
 *     (same for all athletes, curated by the product owner)
 *   - AthleteSyllabusProgress = PRIVATE per-athlete progress
 *     (stored separately, never mixed into shared definitions)
 *
 * Requirements reference canonical map/reference identifiers:
 *   - sectionId: matches ReferenceSection.id (e.g. 'dominant_positions')
 *   - positionName: matches ReferencePosition.name (e.g. 'Mount')
 *   - heading: matches standard headings (e.g. 'Submissions')
 *   - techniqueName: matches technique labels from REFERENCE_TECHNIQUES
 *
 * Progress key format is compatible with reference-progress-store:
 *   tech|<section>|<position>|<role>|<heading>|<technique>
 */
Object.defineProperty(exports, "__esModule", { value: true });
