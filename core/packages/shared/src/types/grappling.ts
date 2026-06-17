/** A single technique node in the SECTIONS tree */
export interface TechniqueNode {
  label: string;
  children?: TechniqueNode[];
  notes?: string;
}

/** A section in the grappling map (Guard, Wrestling, etc.) */
export interface Section {
  title: string;
  color: string;
  nodes: TechniqueNode[];
}

/**
 * Technique key — pipe-delimited, KEY_VERSION=2.
 * Format: section|position|perspective|heading|itemLabel
 */
export type TechniqueKey = string;

/** Transition edge in the 3D graph */
export interface TransitionEdge {
  source: string; // canonical position name
  target: string; // canonical position name
  label: string; // context-specific label
  weight: number; // count of same (label -> target)
}
