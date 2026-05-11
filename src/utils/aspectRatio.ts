import type { BorderConfig } from '../types';

export function calculateFixedAspectRatio(
  border: BorderConfig,
  imageWidth: number,
  imageHeight: number
): BorderConfig {
  const { fixedParam } = border;
  const W = imageWidth;
  const H = imageHeight;

  let { top: b, bottom: c, left: a } = border;

  if (fixedParam === 'a') {
    a = Math.round((W * (b + c)) / (2 * H));
    return { ...border, left: a, right: a };
  } else if (fixedParam === 'b') {
    b = Math.round((2 * a * H) / W - c);
    if (b < 0) b = 0;
    return { ...border, top: b };
  } else {
    // fixedParam === 'c'
    c = Math.round((2 * a * H) / W - b);
    if (c < 0) c = 0;
    return { ...border, bottom: c };
  }
}

export function getOutputDimensions(border: BorderConfig, imageWidth: number, imageHeight: number) {
  return {
    width: imageWidth + border.left + border.right,
    height: imageHeight + border.top + border.bottom,
  };
}
