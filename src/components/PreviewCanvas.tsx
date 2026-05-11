import { useEffect, useRef } from 'react';
import type { ImageConfig } from '../types';
import { renderPreviewComposite } from '../utils/render';

interface Props {
  image: ImageConfig;
}

export default function PreviewCanvas({ image }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const debounceRef = useRef<number | null>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);

    debounceRef.current = window.setTimeout(() => {
      renderPreview();
    }, 300);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [
    image.border,
    image.logos,
    image.textElements,
    image.textLayout,
    image.width,
    image.height,
  ]);

  async function renderPreview() {
    if (!canvasRef.current) return;
    const canvas = canvasRef.current;
    try {
      const rendered = await renderPreviewComposite(
        image.border,
        image.logos,
        image.textElements,
        image.textLayout,
        image.width,
        image.height,
        800
      );
      const displayCtx = canvas.getContext('2d')!;
      canvas.width = rendered.width;
      canvas.height = rendered.height;
      displayCtx.drawImage(rendered, 0, 0);
    } catch {
      // Ignore rendering errors during preview
    }
  }

  const outputW = image.width + image.border.left + image.border.right;
  const outputH = image.height + image.border.top + image.border.bottom;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-slate-700 text-sm uppercase tracking-wide">
          Live Preview
        </h3>
        <span className="text-xs text-slate-400">
          {outputW} × {outputH} px
        </span>
      </div>
      <div className="bg-slate-100 rounded-lg flex items-center justify-center min-h-[200px] overflow-auto">
        <canvas
          ref={canvasRef}
          className="max-w-full h-auto"
          style={{ imageRendering: 'auto' }}
        />
      </div>
    </div>
  );
}
