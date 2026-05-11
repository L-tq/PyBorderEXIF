import { useRef, useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppState } from '../context/AppContext';
import { renderComposite } from '../utils/render';
import { loadImage } from '../utils/render';

export default function ReviewPage() {
  const { state, dispatch } = useAppState();
  const navigate = useNavigate();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [currentImageIdx, setCurrentImageIdx] = useState(0);
  const [rendered, setRendered] = useState(false);
  const [rendering, setRendering] = useState(false);

  const image = state.images[currentImageIdx];

  const renderFull = useCallback(async () => {
    if (!image || !canvasRef.current) return;
    setRendering(true);
    try {
      const img = await loadImage(image.dataUrl);
      await renderComposite(
        canvasRef.current!,
        img,
        image.border,
        image.logos,
        image.textElements,
        image.textLayout,
        image.width,
        image.height
      );
      setRendered(true);
    } catch (err) {
      console.error('Render error:', err);
    }
    setRendering(false);
  }, [image]);

  const download = useCallback(
    (format: 'jpeg' | 'png') => {
      if (!canvasRef.current) return;
      const mime = format === 'jpeg' ? 'image/jpeg' : 'image/png';
      const ext = format === 'jpeg' ? 'jpg' : 'png';
      const dataUrl = canvasRef.current.toDataURL(mime, 0.95);
      const link = document.createElement('a');
      const originalName = image.file.name.replace(/\.[^.]+$/, '');
      link.download = `${originalName}_framed.${ext}`;
      link.href = dataUrl;
      link.click();
    },
    [image]
  );

  if (!image) {
    return (
      <div className="max-w-5xl mx-auto p-6 text-center">
        <p className="text-slate-500">No images loaded.</p>
        <button
          onClick={() => {
            dispatch({ type: 'SET_STEP', payload: 1 });
            navigate('/');
          }}
          className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-lg"
        >
          Go to File Selection
        </button>
      </div>
    );
  }

  const outputW = image.width + image.border.left + image.border.right;
  const outputH = image.height + image.border.top + image.border.bottom;

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-slate-800">
            Step 3: Review & Download
          </h1>
          {state.images.length > 1 && (
            <div className="flex items-center gap-1">
              {state.images.map((img, i) => (
                <button
                  key={img.id}
                  onClick={() => {
                    setCurrentImageIdx(i);
                    setRendered(false);
                  }}
                  className={`px-3 py-1.5 text-xs rounded-lg ${
                    i === currentImageIdx
                      ? 'bg-blue-500 text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {img.file.name.slice(0, 15)}
                  {img.file.name.length > 15 ? '…' : ''}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => {
              dispatch({ type: 'SET_STEP', payload: 2 });
              navigate('/edit');
            }}
            className="px-4 py-2 text-sm text-slate-600 hover:text-slate-800"
          >
            ← Back to Layout
          </button>
          {rendered && (
            <>
              <button
                onClick={() => download('jpeg')}
                className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700"
              >
                Download JPEG
              </button>
              <button
                onClick={() => download('png')}
                className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700"
              >
                Download PNG
              </button>
            </>
          )}
        </div>
      </div>

      {!rendered && (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
          <p className="text-slate-500 mb-4">
            Full-resolution preview not yet rendered.
          </p>
          <p className="text-xs text-slate-400 mb-4">
            Output: {outputW} × {outputH} px
          </p>
          <button
            onClick={renderFull}
            disabled={rendering}
            className="px-6 py-3 bg-blue-500 text-white rounded-lg font-medium hover:bg-blue-600 disabled:opacity-50"
          >
            {rendering ? (
              <span className="flex items-center gap-2">
                <span className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
                Rendering...
              </span>
            ) : (
              'Render Full Resolution'
            )}
          </button>
        </div>
      )}

      <div
        className={`bg-white rounded-xl border border-slate-200 p-6 overflow-auto ${
          rendered ? '' : 'hidden'
        }`}
      >
        <canvas
          ref={canvasRef}
          className="max-w-full h-auto mx-auto"
        />
      </div>
    </div>
  );
}
