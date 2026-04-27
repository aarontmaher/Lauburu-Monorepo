/**
 * Lazy-loaded image picker + compressor for tester feedback.
 *
 * Native modules are required lazily so Expo Go doesn't crash on
 * import, and so the feedback bubble compiles even when photo
 * support is not wired in a given build.
 *
 * Flow:
 *   1. Request permission (camera or library).
 *   2. Launch picker.
 *   3. Resize max dimension to 1200px and JPEG-compress at 0.6.
 *   4. Return { mime, dataBase64, widthPx, heightPx, sizeBytes }.
 *
 * Errors are surfaced as typed results (not thrown) so the caller
 * can keep the feedback form mounted.
 */
import type { FeedbackAttachment } from './tester-feedback';
import { MAX_ATTACHMENT_BYTES } from './tester-feedback';

export type AttachmentSource = 'camera' | 'library';

export type AttachmentResult =
  | { ok: true; attachment: FeedbackAttachment }
  | { ok: false; cancelled: true }
  | { ok: false; error: string };

function picker() {
  return require('expo-image-picker');
}

function manipulator() {
  return require('expo-image-manipulator');
}

async function ensurePermission(source: AttachmentSource): Promise<{ ok: boolean; error?: string }> {
  try {
    const ip = picker();
    if (source === 'camera') {
      const current = await ip.getCameraPermissionsAsync();
      if (current.granted) return { ok: true };
      if (!current.canAskAgain) {
        return { ok: false, error: 'Camera permission is off. Enable it in Settings.' };
      }
      const req = await ip.requestCameraPermissionsAsync();
      return req.granted
        ? { ok: true }
        : { ok: false, error: 'Camera permission denied.' };
    }
    const current = await ip.getMediaLibraryPermissionsAsync();
    if (current.granted) return { ok: true };
    if (!current.canAskAgain) {
      return { ok: false, error: 'Photo library permission is off. Enable it in Settings.' };
    }
    const req = await ip.requestMediaLibraryPermissionsAsync();
    return req.granted
      ? { ok: true }
      : { ok: false, error: 'Photo library permission denied.' };
  } catch (e: any) {
    return { ok: false, error: e?.message ?? 'Permission check failed' };
  }
}

async function compressToAttachment(
  uri: string,
  fallbackMime: 'image/jpeg' | 'image/png',
): Promise<AttachmentResult> {
  try {
    const im = manipulator();
    const result = await im.manipulateAsync(
      uri,
      [{ resize: { width: 1200 } }],
      {
        compress: 0.6,
        format: im.SaveFormat.JPEG,
        base64: true,
      },
    );
    const base64 = typeof result.base64 === 'string' ? result.base64 : '';
    if (!base64) {
      return { ok: false, error: 'Image could not be read.' };
    }
    // Rough bytes from base64: length * 0.75
    const sizeBytes = Math.round(base64.length * 0.75);
    if (sizeBytes > MAX_ATTACHMENT_BYTES) {
      return {
        ok: false,
        error: `Image too large after compression (${Math.round(sizeBytes / 1024)}KB). Try a smaller screenshot.`,
      };
    }
    return {
      ok: true,
      attachment: {
        mime: 'image/jpeg',
        dataBase64: base64,
        widthPx: result.width,
        heightPx: result.height,
        sizeBytes,
      },
    };
  } catch (e: any) {
    return { ok: false, error: e?.message ?? 'Image processing failed' };
  }
}

export async function pickAttachment(source: AttachmentSource): Promise<AttachmentResult> {
  const perm = await ensurePermission(source);
  if (!perm.ok) return { ok: false, error: perm.error ?? 'Permission denied.' };

  try {
    const ip = picker();
    const opts = {
      mediaTypes: ip.MediaTypeOptions?.Images ?? 'Images',
      allowsEditing: false,
      quality: 0.8,
      base64: false,
    };
    const result =
      source === 'camera'
        ? await ip.launchCameraAsync(opts)
        : await ip.launchImageLibraryAsync(opts);

    if (result.canceled) return { ok: false, cancelled: true };
    const asset = result.assets?.[0];
    if (!asset?.uri) return { ok: false, error: 'No image selected.' };

    const mime: 'image/jpeg' | 'image/png' =
      asset.mimeType === 'image/png' ? 'image/png' : 'image/jpeg';
    return compressToAttachment(asset.uri, mime);
  } catch (e: any) {
    return { ok: false, error: e?.message ?? 'Image picker failed' };
  }
}
