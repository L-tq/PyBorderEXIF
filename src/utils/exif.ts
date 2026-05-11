import ExifReader from 'exifreader';

export interface ExifData {
  [key: string]: unknown;
}

export async function parseExif(file: File): Promise<Record<string, unknown>> {
  try {
    const tags = await ExifReader.load(file, { expanded: true });
    const result: Record<string, unknown> = {};

    for (const [key, value] of Object.entries(tags)) {
      if (key === 'MakerNote' || key === 'UserComment') continue;
      result[key] = value;
    }

    return result;
  } catch {
    return {};
  }
}

export function getExifStringValue(exif: Record<string, unknown>, tag: string): string {
  const val = exif[tag];
  if (!val) return '';

  if (typeof val === 'object' && val !== null) {
    const obj = val as Record<string, unknown>;
    if ('description' in obj) return String(obj.description);
    if ('value' in obj) {
      const v = obj.value;
      if (Array.isArray(v)) return v.join(', ');
      return String(v);
    }
    return JSON.stringify(obj);
  }
  return String(val);
}

export function getCameraModel(exif: Record<string, unknown>): string {
  return getExifStringValue(exif, 'Model') || getExifStringValue(exif, 'CameraModelName') || '';
}

export function getLensModel(exif: Record<string, unknown>): string {
  return getExifStringValue(exif, 'LensModel') || getExifStringValue(exif, 'LensSpecification') || '';
}

export function getFocalLength(exif: Record<string, unknown>): string {
  const val = getExifStringValue(exif, 'FocalLength');
  if (!val) return '';
  return val.includes('mm') ? val : `${val}mm`;
}

export function getAperture(exif: Record<string, unknown>): string {
  const val = getExifStringValue(exif, 'FNumber') || getExifStringValue(exif, 'ApertureValue');
  if (!val) return '';
  const num = parseFloat(val);
  return isNaN(num) ? val : `f/${num.toFixed(1)}`;
}

export function getISO(exif: Record<string, unknown>): string {
  const val = getExifStringValue(exif, 'ISOSpeedRatings') || getExifStringValue(exif, 'ISO');
  return val ? `ISO ${val}` : '';
}

export function resolveTextElementValue(
  exif: Record<string, unknown>,
  type: string,
  customTag?: string,
  customLabel?: string,
  authorName?: string
): string {
  switch (type) {
    case 'author':
      return authorName || '';
    case 'camera':
      return getCameraModel(exif);
    case 'lens':
      return getLensModel(exif);
    case 'focal-length':
      return getFocalLength(exif);
    case 'aperture':
      return getAperture(exif);
    case 'iso':
      return getISO(exif);
    case 'custom':
      if (customTag) {
        const val = getExifStringValue(exif, customTag);
        return customLabel ? `${customLabel}: ${val}` : val;
      }
      return '';
    default:
      return '';
  }
}
