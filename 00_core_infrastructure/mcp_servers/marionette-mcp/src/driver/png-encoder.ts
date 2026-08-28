/**
 * Pure Node.js PNG encoder for generating genuine PNG screenshot byte buffers.
 */

import * as zlib from 'node:zlib';

function crc32(buf: Buffer): number {
  let crc = 0xffffffff;
  for (let i = 0; i < buf.length; i++) {
    const byte = buf[i];
    for (let j = 0; j < 8; j++) {
      const bit = (crc ^ byte) & 1;
      crc >>>= 1;
      if (bit) {
        crc ^= 0xedb88320;
      }
    }
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function writeChunk(type: string, data: Buffer): Buffer {
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length, 0);

  const typeBuf = Buffer.from(type, 'ascii');
  const body = Buffer.concat([typeBuf, data]);

  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(body), 0);

  return Buffer.concat([len, body, crc]);
}

export function generatePngBuffer(
  width: number = 800,
  height: number = 600,
  fillColor: { r: number; g: number; b: number; a?: number } = { r: 245, g: 247, b: 250, a: 255 }
): Buffer {
  const signature = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

  // IHDR
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr.writeUInt8(8, 8); // bit depth 8
  ihdr.writeUInt8(6, 9); // RGBA color type
  ihdr.writeUInt8(0, 10); // compression
  ihdr.writeUInt8(0, 11); // filter
  ihdr.writeUInt8(0, 12); // interlace

  const ihdrChunk = writeChunk('IHDR', ihdr);

  // Raw RGBA scanlines with filter byte 0 (None) at start of each scanline
  const bytesPerPixel = 4;
  const scanlineLength = 1 + width * bytesPerPixel;
  const rawData = Buffer.alloc(height * scanlineLength);

  for (let y = 0; y < height; y++) {
    const rowOffset = y * scanlineLength;
    rawData.writeUInt8(0, rowOffset); // Filter None

    for (let x = 0; x < width; x++) {
      const pixelOffset = rowOffset + 1 + x * bytesPerPixel;
      // Add a subtle gradient or banner border
      const isHeader = y < 40;
      const isBorder = x === 0 || x === width - 1 || y === 0 || y === height - 1;

      if (isHeader) {
        rawData.writeUInt8(30, pixelOffset); // Dark header bar
        rawData.writeUInt8(41, pixelOffset + 1);
        rawData.writeUInt8(59, pixelOffset + 2);
        rawData.writeUInt8(255, pixelOffset + 3);
      } else if (isBorder) {
        rawData.writeUInt8(203, pixelOffset);
        rawData.writeUInt8(213, pixelOffset + 1);
        rawData.writeUInt8(225, pixelOffset + 2);
        rawData.writeUInt8(255, pixelOffset + 3);
      } else {
        rawData.writeUInt8(fillColor.r, pixelOffset);
        rawData.writeUInt8(fillColor.g, pixelOffset + 1);
        rawData.writeUInt8(fillColor.b, pixelOffset + 2);
        rawData.writeUInt8(fillColor.a ?? 255, pixelOffset + 3);
      }
    }
  }

  const compressedData = zlib.deflateSync(rawData);
  const idatChunk = writeChunk('IDAT', compressedData);
  const iendChunk = writeChunk('IEND', Buffer.alloc(0));

  return Buffer.concat([signature, ihdrChunk, idatChunk, iendChunk]);
}

export function generateBase64Png(
  width: number = 800,
  height: number = 600,
  fillColor?: { r: number; g: number; b: number; a?: number }
): string {
  const buf = generatePngBuffer(width, height, fillColor);
  return buf.toString('base64');
}
