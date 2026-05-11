import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppState } from '../context/AppContext';
import {
  parseExif,
  getCameraModel,
  getLensModel,
  getFocalLength,
  getAperture,
  getISO,
} from '../utils/exif';
import { loadSettings } from '../utils/cookies';
import { isRawFile, extractRawPreview } from '../utils/raw';
import type { ImageConfig, TextElementConfig } from '../types';

export default function FileUploadPage() {
  const { state, dispatch } = useAppState();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const processFiles = useCallback(
    async (files: FileList) => {
      setLoading(true);
      const imageFiles = Array.from(files).filter(
        (f) =>
          f.type.startsWith('image/') ||
          f.name.toLowerCase().endsWith('.arw') ||
          f.name.toLowerCase().endsWith('.raw') ||
          f.name.toLowerCase().endsWith('.cr2') ||
          f.name.toLowerCase().endsWith('.nef') ||
          f.name.toLowerCase().endsWith('.dng')
      );

      const configs: ImageConfig[] = [];
      const saved = loadSettings();
      for (const file of imageFiles) {
        const isRaw = isRawFile(file.name);
        let dataUrl: string;

        if (isRaw) {
          const preview = await extractRawPreview(file);
          dataUrl = preview
            ? URL.createObjectURL(preview)
            : URL.createObjectURL(file);
        } else {
          dataUrl = URL.createObjectURL(file);
        }

        const exif = await parseExif(file);
        const dimensions = await getImageDimensions(dataUrl);

        const defaultTextElements = buildDefaultTextElements(exif);
        configs.push({
          id: crypto.randomUUID(),
          file,
          dataUrl,
          exif,
          width: dimensions.width,
          height: dimensions.height,
          border: {
            strategy: saved?.border?.strategy || 'custom',
            top: saved?.border?.top ?? 80,
            bottom: saved?.border?.bottom ?? 160,
            left: saved?.border?.left ?? 60,
            right: saved?.border?.right ?? 60,
            color: saved?.border?.color || '#FFFFFF',
            fixedParam: saved?.border?.fixedParam || 'c',
          },
          logos: [],
          textElements: defaultTextElements,
          textLayout: {
            leftMargin: saved?.textLayout?.leftMargin ?? 40,
            rightMargin: saved?.textLayout?.rightMargin ?? 40,
            bottomMargin: saved?.textLayout?.bottomMargin ?? 30,
            lineSpacing: saved?.textLayout?.lineSpacing ?? 4,
          },
        });
      }

      dispatch({ type: 'SET_IMAGES', payload: configs });
      setLoading(false);
    },
    [dispatch]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (e.dataTransfer.files.length) processFiles(e.dataTransfer.files);
    },
    [processFiles]
  );

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files?.length) processFiles(e.target.files);
    },
    [processFiles]
  );

  const removeImage = useCallback(
    (id: string) => dispatch({ type: 'REMOVE_IMAGE', payload: id }),
    [dispatch]
  );

  const canProceed = state.images.length > 0;

  return (
    <div className="max-w-5xl mx-auto p-6">
      <h1 className="text-2xl font-bold text-slate-800 mb-6">
        Step 1: Select Images
      </h1>

      <div
        onDrop={handleDrop}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        className={`border-2 border-dashed rounded-xl p-12 text-center transition-colors cursor-pointer ${
          dragOver
            ? 'border-blue-500 bg-blue-50'
            : 'border-slate-300 hover:border-slate-400 bg-white'
        }`}
        onClick={() => document.getElementById('file-input')?.click()}
      >
        <input
          id="file-input"
          type="file"
          multiple
          accept="image/*,.arw,.raw,.cr2,.nef,.dng"
          onChange={handleFileChange}
          className="hidden"
        />
        <div className="text-4xl mb-4">📁</div>
        <p className="text-slate-600 text-lg mb-2">
          Drop images here or click to browse
        </p>
        <p className="text-slate-400 text-sm">
          JPEG, PNG, ARW, CR2, NEF, DNG supported
        </p>
      </div>

      {loading && (
        <div className="mt-8 text-center text-slate-500">
          <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-2" />
          Processing images...
        </div>
      )}

      {state.images.length > 0 && (
        <div className="mt-8 space-y-6">
          <h2 className="text-lg font-semibold text-slate-700">
            Selected Images ({state.images.length})
          </h2>
          {state.images.map((img, idx) => (
            <div
              key={img.id}
              className="bg-white rounded-xl border border-slate-200 p-6"
            >
              <div className="flex gap-6">
                <img
                  src={img.dataUrl}
                  alt={`Preview ${idx + 1}`}
                  className="w-40 h-32 object-cover rounded-lg border"
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-medium text-slate-800 truncate flex items-center gap-2">
                      {img.file.name}
                      {isRawFile(img.file.name) && (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-700">
                          RAW
                        </span>
                      )}
                    </h3>
                    <button
                      onClick={() => removeImage(img.id)}
                      className="text-red-500 hover:text-red-700 text-sm"
                    >
                      Remove
                    </button>
                  </div>
                  <p className="text-sm text-slate-500">
                    {img.width} × {img.height} px
                  </p>
                  <ExifSummary exif={img.exif} />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-8 flex justify-end">
        <button
          disabled={!canProceed}
          onClick={() => {
            dispatch({ type: 'SET_STEP', payload: 2 });
            navigate('/edit');
          }}
          className="px-6 py-2.5 bg-blue-500 text-white rounded-lg font-medium hover:bg-blue-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          Next: Layout & Preview →
        </button>
      </div>
    </div>
  );
}

function getImageDimensions(src: string): Promise<{ width: number; height: number }> {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve({ width: img.naturalWidth, height: img.naturalHeight });
    img.onerror = () => resolve({ width: 800, height: 600 });
    img.src = src;
  });
}

function buildDefaultTextElements(exif: Record<string, unknown>): TextElementConfig[] {
  const elements: TextElementConfig[] = [];
  let order = 0;

  const presets: { type: TextElementConfig['type']; value: string }[] = [
    { type: 'camera', value: getCameraModel(exif) },
    { type: 'lens', value: getLensModel(exif) },
    { type: 'focal-length', value: getFocalLength(exif) },
    { type: 'aperture', value: getAperture(exif) },
    { type: 'iso', value: getISO(exif) },
  ];

  for (const preset of presets) {
    if (preset.value) {
      elements.push({
        id: crypto.randomUUID(),
        type: preset.type,
        value: preset.value,
        order: order++,
        fontFamily: 'Roboto',
        fontSize: 14,
        fontColor: '#333333',
        fontWeight: 400,
        fontStyle: 'normal',
      });
    }
  }

  return elements;
}

const KEY_LABELS: Record<string, string> = {
  Model: 'Camera',
  LensModel: 'Lens',
  FocalLength: 'Focal Length',
  FNumber: 'Aperture',
  ISOSpeedRatings: 'ISO',
  ExposureTime: 'Shutter Speed',
  DateTimeOriginal: 'Date',
  Make: 'Make',
  ImageWidth: 'Width',
  ImageHeight: 'Height',
  Software: 'Software',
  Artist: 'Artist',
  Copyright: 'Copyright',
  GPSLatitude: 'GPS Lat',
  GPSLongitude: 'GPS Lon',
};

const EXIF_GROUP_KEYS = new Set([
  'file', 'jfif', 'icc', 'composite', 'exif', 'iptc', 'xmp',
  'MakerNote', 'UserComment', 'thumbnail', 'Thumbnail',
]);

function formatExifValue(_key: string, value: unknown): string {
  if (typeof value === 'object' && value !== null) {
    const obj = value as Record<string, unknown>;
    if ('description' in obj) return String(obj.description);
    if ('value' in obj) {
      const v = obj.value;
      if (Array.isArray(v)) return v.join(', ');
      return String(v);
    }
    // Group object without direct value — skip
    return '';
  }
  return String(value);
}

function ExifSummary({ exif }: { exif: Record<string, unknown> }) {
  const keys = Object.keys(exif).filter(
    (k) => !EXIF_GROUP_KEYS.has(k) && formatExifValue(k, exif[k]).length > 0
  );
  const displayKeys = keys.filter((k) => KEY_LABELS[k]);
  const otherKeys = keys.filter((k) => !KEY_LABELS[k]);

  const sorted = [...displayKeys, ...otherKeys].slice(0, 20);

  if (sorted.length === 0) {
    return <p className="text-xs text-slate-400 mt-1">No EXIF data found</p>;
  }

  return (
    <div className="mt-2 max-h-32 overflow-y-auto">
      <table className="text-xs w-full">
        <tbody>
          {sorted.map((key) => (
            <tr key={key} className="border-b border-slate-100">
              <td className="py-1 pr-3 text-slate-400 font-medium whitespace-nowrap">
                {KEY_LABELS[key] || key}
              </td>
              <td className="py-1 text-slate-600 break-all">
                {formatExifValue(key, exif[key])}
              </td>
            </tr>
          ))}
          {keys.length > 20 && (
            <tr>
              <td colSpan={2} className="py-1 text-slate-400 italic">
                +{keys.length - 20} more tags
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
