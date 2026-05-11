import type { LogoConfig } from '../types';
import { useAppState } from '../context/AppContext';

interface Props {
  logos: LogoConfig[];
  imageId: string;
}

export default function LogoManager({ logos, imageId }: Props) {
  const { dispatch } = useAppState();

  const addLogo = (files: FileList) => {
    Array.from(files).forEach((file) => {
      if (!file.type.startsWith('image/')) return;
      const reader = new FileReader();
      reader.onload = () => {
        const dataUrl = reader.result as string;
        const img = new Image();
        img.onload = () => {
          dispatch({
            type: 'ADD_LOGO',
            payload: {
              imageId,
              logo: {
                id: crypto.randomUUID(),
                dataUrl,
                fileName: file.name,
                relX: 0.5,
                relY: 0.5,
                offsetX: 0,
                offsetY: 0,
                scale: 50,
                originalWidth: img.naturalWidth,
                originalHeight: img.naturalHeight,
              },
            },
          });
        };
        img.src = dataUrl;
      };
      reader.readAsDataURL(file);
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-slate-700 text-sm uppercase tracking-wide">
          Logos ({logos.length})
        </h3>
        <label className="px-3 py-1.5 bg-blue-500 text-white text-xs rounded-lg cursor-pointer hover:bg-blue-600 transition-colors">
          + Add Logo
          <input
            type="file"
            accept="image/png,image/jpeg,image/svg+xml"
            className="hidden"
            onChange={(e) => e.target.files && addLogo(e.target.files)}
          />
        </label>
      </div>

      {logos.map((logo) => (
        <LogoItem key={logo.id} logo={logo} imageId={imageId} />
      ))}

      {logos.length === 0 && (
        <p className="text-xs text-slate-400 italic">No logos added</p>
      )}
    </div>
  );
}

function LogoItem({ logo, imageId }: { logo: LogoConfig; imageId: string }) {
  const { dispatch } = useAppState();

  const update = (updates: Partial<LogoConfig>) => {
    dispatch({
      type: 'UPDATE_LOGO',
      payload: { imageId, logoId: logo.id, updates },
    });
  };

  const remove = () => {
    dispatch({ type: 'REMOVE_LOGO', payload: { imageId, logoId: logo.id } });
  };

  return (
    <div className="bg-slate-50 rounded-lg p-3 border border-slate-200 space-y-2">
      <div className="flex items-center gap-2">
        <img
          src={logo.dataUrl}
          alt={logo.fileName}
          className="w-8 h-8 object-contain rounded"
        />
        <span className="text-xs text-slate-600 truncate flex-1">
          {logo.fileName}
        </span>
        <button
          onClick={remove}
          className="text-red-400 hover:text-red-600 text-xs"
        >
          ✕
        </button>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-xs text-slate-400">rel X (0-1)</label>
          <input
            type="number"
            min={0}
            max={1}
            step={0.01}
            value={logo.relX}
            onChange={(e) => update({ relX: Number(e.target.value) })}
            className="w-full border border-slate-300 rounded px-2 py-1 text-xs"
          />
        </div>
        <div>
          <label className="text-xs text-slate-400">rel Y (0-1)</label>
          <input
            type="number"
            min={0}
            max={1}
            step={0.01}
            value={logo.relY}
            onChange={(e) => update({ relY: Number(e.target.value) })}
            className="w-full border border-slate-300 rounded px-2 py-1 text-xs"
          />
        </div>
        <div>
          <label className="text-xs text-slate-400">Offset X (px)</label>
          <input
            type="number"
            value={logo.offsetX}
            onChange={(e) => update({ offsetX: Number(e.target.value) })}
            className="w-full border border-slate-300 rounded px-2 py-1 text-xs"
          />
        </div>
        <div>
          <label className="text-xs text-slate-400">Offset Y (px)</label>
          <input
            type="number"
            value={logo.offsetY}
            onChange={(e) => update({ offsetY: Number(e.target.value) })}
            className="w-full border border-slate-300 rounded px-2 py-1 text-xs"
          />
        </div>
      </div>

      <div>
        <label className="text-xs text-slate-400">
          Scale: {logo.scale}%
        </label>
        <input
          type="range"
          min={5}
          max={200}
          value={logo.scale}
          onChange={(e) => update({ scale: Number(e.target.value) })}
          className="w-full"
        />
      </div>
    </div>
  );
}
