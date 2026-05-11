import type { BorderConfig, LogoConfig, TextElementConfig, TextLayout } from '../types';
import { calculateFixedAspectRatio } from './aspectRatio';

export async function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = src;
  });
}

function wrapText(
  ctx: CanvasRenderingContext2D,
  text: string,
  maxWidth: number
): string[] {
  const lines: string[] = [];
  for (const paragraph of text.split('\n')) {
    if (paragraph === '') {
      lines.push('');
      continue;
    }
    const words = paragraph.split('');
    let line = '';
    for (const char of words) {
      const testLine = line + char;
      const metrics = ctx.measureText(testLine);
      if (metrics.width > maxWidth && line.length > 0) {
        lines.push(line);
        line = char;
      } else {
        line = testLine;
      }
    }
    if (line) lines.push(line);
  }
  return lines;
}

export async function renderComposite(
  canvas: HTMLCanvasElement,
  imageData: HTMLImageElement | ImageData,
  border: BorderConfig,
  logos: LogoConfig[],
  textElements: TextElementConfig[],
  textLayout: TextLayout,
  imageWidth: number,
  imageHeight: number,
  skipImage = false
): Promise<void> {
  const effectiveBorder =
    border.strategy === 'fixed-aspect-ratio'
      ? calculateFixedAspectRatio(border, imageWidth, imageHeight)
      : border;

  const outW = imageWidth + effectiveBorder.left + effectiveBorder.right;
  const outH = imageHeight + effectiveBorder.top + effectiveBorder.bottom;
  canvas.width = outW;
  canvas.height = outH;

  const ctx = canvas.getContext('2d')!;

  // Fill border
  ctx.fillStyle = effectiveBorder.color;
  ctx.fillRect(0, 0, outW, outH);

  // Draw image centered within borders (or dashed placeholder for preview)
  const imgX = effectiveBorder.left;
  const imgY = effectiveBorder.top;

  if (skipImage) {
    // Dashed box placeholder
    ctx.save();
    ctx.setLineDash([6, 4]);
    ctx.strokeStyle = '#94a3b8';
    ctx.lineWidth = 1;
    ctx.strokeRect(imgX + 0.5, imgY + 0.5, imageWidth, imageHeight);
    ctx.setLineDash([]);
    ctx.fillStyle = '#94a3b8';
    ctx.font = '14px Roboto, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('Original Image', imgX + imageWidth / 2, imgY + imageHeight / 2);
    ctx.restore();
  } else if (imageData instanceof HTMLImageElement) {
    ctx.drawImage(imageData, imgX, imgY, imageWidth, imageHeight);
  } else {
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = imageWidth;
    tempCanvas.height = imageHeight;
    const tempCtx = tempCanvas.getContext('2d')!;
    tempCtx.putImageData(imageData, 0, 0);
    ctx.drawImage(tempCanvas, imgX, imgY, imageWidth, imageHeight);
  }

  // Draw logos (preload all images first)
  const borderLeft = effectiveBorder.left;
  const borderBottom = effectiveBorder.bottom;

  const loadedLogos = await Promise.all(
    logos.map(async (logo) => {
      try {
        const img = await loadImage(logo.dataUrl);
        return { img, logo };
      } catch {
        return null;
      }
    })
  );

  for (const item of loadedLogos) {
    if (!item) continue;
    const { img, logo } = item;

    const logoW = logo.originalWidth * (logo.scale / 100);
    const logoH = logo.originalHeight * (logo.scale / 100);

    // relX/relY relative to left-bottom of border
    // relX: 0 = left edge of border, 1 = right edge of border
    // relY: 0 = bottom edge of border, 1 = top edge of border
    const baseX = borderLeft * logo.relX;
    const baseY = outH - borderBottom * logo.relY - logoH;
    const x = baseX + logo.offsetX;
    const y = baseY - logo.offsetY;

    ctx.drawImage(img, x, y, logoW, logoH);
  }

  // Draw text elements in bottom border
  const bottomAreaTop = outH - borderBottom;
  const textAreaWidth = outW - textLayout.leftMargin - textLayout.rightMargin;
  const textStartX = textLayout.leftMargin;

  let yPos = outH - textLayout.bottomMargin;
  const sortedElements = [...textElements].sort((a, b) => b.order - a.order);

  for (let i = sortedElements.length - 1; i >= 0; i--) {
    const el = sortedElements[i];
    if (!el.value) continue;

    const fontStyle = `${el.fontStyle} ${el.fontWeight} ${el.fontSize}px "${el.fontFamily}"`;
    ctx.font = fontStyle;
    ctx.fillStyle = el.fontColor;
    ctx.textBaseline = 'bottom';

    const lines = wrapText(ctx, el.value, textAreaWidth);
    const lineHeight = el.fontSize + textLayout.lineSpacing;

    for (let j = lines.length - 1; j >= 0; j--) {
      if (yPos - lineHeight < bottomAreaTop + 10) break;
      ctx.fillText(lines[j], textStartX, yPos);
      yPos -= lineHeight;
    }
  }
}

export async function renderPreviewComposite(
  border: BorderConfig,
  logos: LogoConfig[],
  textElements: TextElementConfig[],
  textLayout: TextLayout,
  imageWidth: number,
  imageHeight: number,
  maxPreviewWidth = 800
): Promise<HTMLCanvasElement> {
  const totalW = imageWidth + border.left + border.right;
  const scale = Math.min(1, maxPreviewWidth / totalW);

  const scaledW = Math.round(imageWidth * scale);
  const scaledH = Math.round(imageHeight * scale);

  const previewBorder: BorderConfig = {
    ...border,
    left: Math.round(border.left * scale),
    right: Math.round(border.right * scale),
    top: Math.round(border.top * scale),
    bottom: Math.round(border.bottom * scale),
  };

  const previewTextLayout: TextLayout = {
    leftMargin: Math.round(textLayout.leftMargin * scale),
    rightMargin: Math.round(textLayout.rightMargin * scale),
    bottomMargin: Math.round(textLayout.bottomMargin * scale),
    lineSpacing: Math.round(textLayout.lineSpacing * scale),
  };

  const previewElements = textElements.map((el) => ({
    ...el,
    fontSize: Math.max(6, Math.round(el.fontSize * scale)),
  }));

  const previewLogos = logos.map((l) => ({
    ...l,
    offsetX: Math.round(l.offsetX * scale),
    offsetY: Math.round(l.offsetY * scale),
    scale: l.scale,
  }));

  // Use a placeholder for the image area — no actual image loading needed
  const placeholder = new Image();
  placeholder.src = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';

  const canvas = document.createElement('canvas');
  await renderComposite(canvas, placeholder, previewBorder, previewLogos, previewElements, previewTextLayout, scaledW, scaledH, true);
  return canvas;
}
