import type { BorderConfig as BorderConfigType } from '../types';
import { useAppState } from '../context/AppContext';

interface Props {
  border: BorderConfigType;
  imageId: string;
}

export default function BorderConfigPanel({ border, imageId }: Props) {
  const { dispatch } = useAppState();

  const update = (updates: Partial<BorderConfigType>) => {
    dispatch({ type: 'UPDATE_BORDER', payload: { imageId, border: updates } });
  };

  return (
    <div className="space-y-4">
      <h3 className="font-semibold text-slate-700 text-sm uppercase tracking-wide">
        Border Settings
      </h3>

      <div>
        <label className="text-xs text-slate-500 block mb-1">Strategy</label>
        <select
          value={border.strategy}
          onChange={(e) =>
            update({ strategy: e.target.value as 'custom' | 'fixed-aspect-ratio' })
          }
          className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white"
        >
          <option value="custom">Custom Dimensions</option>
          <option value="fixed-aspect-ratio">Fixed Aspect Ratio</option>
        </select>
      </div>

      {border.strategy === 'fixed-aspect-ratio' && (
        <div>
          <label className="text-xs text-slate-500 block mb-1">
            Auto-Calculate
          </label>
          <select
            value={border.fixedParam || 'c'}
            onChange={(e) =>
              update({ fixedParam: e.target.value as 'a' | 'b' | 'c' })
            }
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white"
          >
            <option value="a">a (left/right) — auto from b + c</option>
            <option value="b">b (top) — auto from a + c</option>
            <option value="c">c (bottom) — auto from a + b</option>
          </select>
          <p className="text-xs text-slate-400 mt-1">
            2·a·H = W·(b + c)
          </p>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-slate-500 block mb-1">
            Top (b){border.strategy === 'fixed-aspect-ratio' && border.fixedParam === 'b' ? ' [auto]' : ''}
          </label>
          <input
            type="number"
            min={0}
            max={2000}
            value={border.top}
            disabled={border.strategy === 'fixed-aspect-ratio' && border.fixedParam === 'b'}
            onChange={(e) => update({ top: Number(e.target.value) || 0 })}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-400"
          />
        </div>
        <div>
          <label className="text-xs text-slate-500 block mb-1">
            Bottom (c){border.strategy === 'fixed-aspect-ratio' && border.fixedParam === 'c' ? ' [auto]' : ''}
          </label>
          <input
            type="number"
            min={0}
            max={2000}
            value={border.bottom}
            disabled={border.strategy === 'fixed-aspect-ratio' && border.fixedParam === 'c'}
            onChange={(e) => update({ bottom: Number(e.target.value) || 0 })}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-400"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-slate-500 block mb-1">
            Left (a){border.strategy === 'fixed-aspect-ratio' && border.fixedParam === 'a' ? ' [auto]' : ''}
          </label>
          <input
            type="number"
            min={0}
            max={2000}
            value={border.left}
            disabled={border.strategy === 'fixed-aspect-ratio' && border.fixedParam === 'a'}
            onChange={(e) => update({ left: Number(e.target.value) || 0 })}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-400"
          />
        </div>
        <div>
          <label className="text-xs text-slate-500 block mb-1">
            Right (a){border.strategy === 'fixed-aspect-ratio' && border.fixedParam === 'a' ? ' [auto]' : ''}
          </label>
          <input
            type="number"
            min={0}
            max={2000}
            value={border.right}
            disabled={border.strategy === 'fixed-aspect-ratio' && border.fixedParam === 'a'}
            onChange={(e) => update({ right: Number(e.target.value) || 0 })}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-400"
          />
        </div>
      </div>

      <div>
        <label className="text-xs text-slate-500 block mb-1">Border Color</label>
        <div className="flex gap-2">
          <input
            type="color"
            value={border.color}
            onChange={(e) => update({ color: e.target.value })}
            className="w-10 h-10 rounded border border-slate-300 cursor-pointer"
          />
          <input
            type="text"
            value={border.color}
            onChange={(e) => update({ color: e.target.value })}
            className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm uppercase"
          />
        </div>
      </div>
    </div>
  );
}
