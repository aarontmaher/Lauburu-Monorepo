"use strict";
/**
 * Video attachment types — truthful availability model for
 * technique/requirement video content.
 *
 * Three states:
 *   attached_ready       — video exists and is playable
 *   attached_unavailable — video reference exists but is not playable
 *   not_attached         — no video is linked to this item
 *
 * Mobile must NOT infer attachment from a bare URL.
 * Only backend/curator can set attached_ready.
 */
Object.defineProperty(exports, "__esModule", { value: true });
