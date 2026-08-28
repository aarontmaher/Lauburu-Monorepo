import test from 'node:test';
import assert from 'node:assert';
import { generatePngBuffer, generateBase64Png } from '../src/driver/png-encoder.js';

test('PNG Encoder: generates valid PNG buffer with proper signature', () => {
  const buf = generatePngBuffer(400, 300);
  assert.ok(buf.length > 0, 'Buffer should not be empty');

  // Verify PNG 8-byte signature: 0x89 0x50 0x4E 0x47 0x0D 0x0A 0x1A 0x0A
  const expectedSig = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];
  for (let i = 0; i < 8; i++) {
    assert.strictEqual(buf[i], expectedSig[i], `Signature byte ${i} must match PNG spec`);
  }

  // Verify IHDR chunk
  const ihdrChunkType = buf.toString('ascii', 12, 16);
  assert.strictEqual(ihdrChunkType, 'IHDR', 'First chunk must be IHDR');

  const width = buf.readUInt32BE(16);
  const height = buf.readUInt32BE(20);
  assert.strictEqual(width, 400, 'Width must match requested width');
  assert.strictEqual(height, 300, 'Height must match requested height');
});

test('PNG Encoder: generates valid base64 PNG string', () => {
  const b64 = generateBase64Png(200, 150);
  assert.ok(typeof b64 === 'string', 'Base64 output must be string');
  assert.ok(b64.length > 50, 'Base64 string must have content');

  const decoded = Buffer.from(b64, 'base64');
  assert.strictEqual(decoded[0], 0x89, 'Decoded buffer must start with PNG magic byte');
});
