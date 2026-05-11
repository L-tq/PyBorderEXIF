const RAW_EXTENSIONS = ['.arw', '.cr2', '.nef', '.dng', '.raw', '.orf', '.rw2', '.pef'];

export function isRawFile(filename: string): boolean {
  const lower = filename.toLowerCase();
  return RAW_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

function findJpegRange(buffer: ArrayBuffer): { start: number; end: number } | null {
  const data = new DataView(buffer);
  const len = data.byteLength;

  for (let i = 0; i < len - 1; i++) {
    if (data.getUint8(i) === 0xff && data.getUint8(i + 1) === 0xd8) {
      let j = i + 2;
      while (j < len - 1) {
        const b0 = data.getUint8(j);
        const b1 = data.getUint8(j + 1);

        if (b0 === 0xff && b1 === 0xd9) {
          return { start: i, end: j + 2 };
        }
        // Skip past SOS (Start of Scan) marker data
        if (b0 === 0xff && b1 === 0xda) {
          j += 2;
          while (j < len - 1) {
            const s0 = data.getUint8(j);
            const s1 = data.getUint8(j + 1);
            if (s0 === 0xff && s1 !== 0x00 && s1 !== 0xff) {
              break;
            }
            j++;
          }
        } else {
          if (j + 2 >= len) break;
          const segLen = (data.getUint8(j + 2) << 8) | data.getUint8(j + 3);
          j += 2 + segLen;
        }
      }
      break;
    }
  }
  return null;
}

export async function extractRawPreview(file: File): Promise<Blob | null> {
  try {
    const buffer = await file.arrayBuffer();
    const jpegRange = findJpegRange(buffer);
    if (!jpegRange) return null;
    return new Blob([buffer.slice(jpegRange.start, jpegRange.end)], { type: 'image/jpeg' });
  } catch {
    return null;
  }
}
