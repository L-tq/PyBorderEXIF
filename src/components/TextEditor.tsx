import { useState } from 'react';
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import type { TextElementConfig, TextLayout, TextElementType } from '../types';
import { useAppState } from '../context/AppContext';
import { resolveTextElementValue } from '../utils/exif';

const FONT_FAMILIES = ['Roboto', 'Source Han Sans SC'];
const FONT_WEIGHTS = [100, 300, 400, 500, 700, 900];

interface Props {
  elements: TextElementConfig[];
  layout: TextLayout;
  imageId: string;
  exif: Record<string, unknown>;
  authorName: string;
  onAuthorChange: (name: string) => void;
}

export default function TextEditor({
  elements,
  layout,
  imageId,
  exif,
  authorName,
  onAuthorChange,
}: Props) {
  const { dispatch } = useAppState();
  const [showAddMenu, setShowAddMenu] = useState(false);
  const [customTag, setCustomTag] = useState('');
  const [customLabel, setCustomLabel] = useState('');

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  );

  const updateLayout = (updates: Partial<TextLayout>) => {
    dispatch({
      type: 'UPDATE_TEXT_LAYOUT',
      payload: { imageId, layout: updates },
    });
  };

  const addElement = (type: TextElementType, customTagName?: string, customTagLabel?: string) => {
    const value = resolveTextElementValue(
      exif,
      type,
      customTagName,
      customTagLabel,
      authorName
    );
    const element: TextElementConfig = {
      id: crypto.randomUUID(),
      type,
      customTag: customTagName,
      customLabel: customTagLabel,
      value,
      order: elements.length,
      fontFamily: 'Roboto',
      fontSize: 14,
      fontColor: '#333333',
      fontWeight: 400,
      fontStyle: 'normal',
    };
    dispatch({ type: 'ADD_TEXT_ELEMENT', payload: { imageId, element } });
    setShowAddMenu(false);
    setCustomTag('');
    setCustomLabel('');
  };

  const removeElement = (elementId: string) => {
    dispatch({
      type: 'REMOVE_TEXT_ELEMENT',
      payload: { imageId, elementId },
    });
  };

  const updateElement = (elementId: string, updates: Partial<TextElementConfig>) => {
    dispatch({
      type: 'UPDATE_TEXT_ELEMENT',
      payload: { imageId, elementId, updates },
    });
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = elements.findIndex((el) => el.id === active.id);
    const newIndex = elements.findIndex((el) => el.id === over.id);

    const reordered = [...elements];
    const [moved] = reordered.splice(oldIndex, 1);
    reordered.splice(newIndex, 0, moved);
    const withOrder = reordered.map((el, i) => ({ ...el, order: i }));

    dispatch({
      type: 'REORDER_TEXT_ELEMENTS',
      payload: { imageId, elements: withOrder },
    });
  };

  const PRESET_TYPES: { type: TextElementType; label: string }[] = [
    { type: 'author', label: 'Author Name' },
    { type: 'camera', label: 'Camera Model' },
    { type: 'lens', label: 'Lens Model' },
    { type: 'focal-length', label: 'Focal Length' },
    { type: 'aperture', label: 'Aperture (f-number)' },
    { type: 'iso', label: 'ISO' },
  ];

  const EXIF_TAGS = Object.keys(exif).filter(
    (k) => !['MakerNote', 'UserComment', 'thumbnail', 'Thumbnail'].includes(k)
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-slate-700 text-sm uppercase tracking-wide">
          Text Elements
        </h3>
        <div className="relative">
          <button
            onClick={() => setShowAddMenu(!showAddMenu)}
            className="px-3 py-1.5 bg-blue-500 text-white text-xs rounded-lg hover:bg-blue-600 transition-colors"
          >
            + Add Text
          </button>
          {showAddMenu && (
            <div className="absolute right-0 top-full mt-1 w-64 bg-white rounded-lg shadow-lg border border-slate-200 z-20 p-3 space-y-2">
              <p className="text-xs text-slate-500 font-medium">Preset Fields</p>
              {PRESET_TYPES.map((preset) => (
                <button
                  key={preset.type}
                  onClick={() => addElement(preset.type)}
                  className="block w-full text-left px-2 py-1 text-xs hover:bg-slate-100 rounded"
                >
                  {preset.label}
                </button>
              ))}
              <hr className="border-slate-200" />
              <p className="text-xs text-slate-500 font-medium">Custom EXIF Tag</p>
              <select
                value={customTag}
                onChange={(e) => setCustomTag(e.target.value)}
                className="w-full border border-slate-300 rounded px-2 py-1 text-xs"
              >
                <option value="">Select tag...</option>
                {EXIF_TAGS.map((tag) => (
                  <option key={tag} value={tag}>
                    {tag}
                  </option>
                ))}
              </select>
              <input
                type="text"
                placeholder="Label (optional)"
                value={customLabel}
                onChange={(e) => setCustomLabel(e.target.value)}
                className="w-full border border-slate-300 rounded px-2 py-1 text-xs"
              />
              <button
                onClick={() => customTag && addElement('custom', customTag, customLabel)}
                disabled={!customTag}
                className="w-full px-2 py-1 bg-slate-100 text-xs rounded hover:bg-slate-200 disabled:opacity-40"
              >
                Add Custom Tag
              </button>
            </div>
          )}
        </div>
      </div>

      {elements.some((el) => el.type === 'author') && (
        <div>
          <label className="text-xs text-slate-500 block mb-1">Author Name</label>
          <input
            type="text"
            value={authorName}
            onChange={(e) => {
              onAuthorChange(e.target.value);
              elements
                .filter((el) => el.type === 'author')
                .forEach((el) => {
                  updateElement(el.id, { value: e.target.value });
                });
            }}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
            placeholder="Enter author name"
          />
        </div>
      )}

      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext
          items={elements.map((el) => el.id)}
          strategy={verticalListSortingStrategy}
        >
          <div className="space-y-2">
            {elements.map((el) => (
              <SortableTextItem
                key={el.id}
                element={el}
                onUpdate={(u) => updateElement(el.id, u)}
                onRemove={() => removeElement(el.id)}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>

      {elements.length === 0 && (
        <p className="text-xs text-slate-400 italic">No text elements added</p>
      )}

      {elements.length > 0 && (
        <div className="border-t border-slate-200 pt-3 space-y-2">
          <h4 className="text-xs font-semibold text-slate-500 uppercase">Layout</h4>
          <div className="grid grid-cols-3 gap-2">
            <div>
              <label className="text-xs text-slate-400">Left Margin</label>
              <input
                type="number"
                min={0}
                value={layout.leftMargin}
                onChange={(e) => updateLayout({ leftMargin: Number(e.target.value) })}
                className="w-full border border-slate-300 rounded px-2 py-1 text-xs"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400">Right Margin</label>
              <input
                type="number"
                min={0}
                value={layout.rightMargin}
                onChange={(e) => updateLayout({ rightMargin: Number(e.target.value) })}
                className="w-full border border-slate-300 rounded px-2 py-1 text-xs"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400">Bottom Margin</label>
              <input
                type="number"
                min={0}
                value={layout.bottomMargin}
                onChange={(e) => updateLayout({ bottomMargin: Number(e.target.value) })}
                className="w-full border border-slate-300 rounded px-2 py-1 text-xs"
              />
            </div>
          </div>
          <div>
            <label className="text-xs text-slate-400">Line Spacing (px)</label>
            <input
              type="number"
              min={0}
              max={50}
              value={layout.lineSpacing}
              onChange={(e) => updateLayout({ lineSpacing: Number(e.target.value) })}
              className="w-full border border-slate-300 rounded px-2 py-1 text-xs"
            />
          </div>
        </div>
      )}
    </div>
  );
}

function SortableTextItem({
  element,
  onUpdate,
  onRemove,
}: {
  element: TextElementConfig;
  onUpdate: (u: Partial<TextElementConfig>) => void;
  onRemove: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition } =
    useSortable({ id: element.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const [expanded, setExpanded] = useState(false);

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="bg-slate-50 rounded-lg border border-slate-200"
    >
      <div className="flex items-center gap-2 p-2">
        <button
          {...attributes}
          {...listeners}
          className="cursor-grab text-slate-400 hover:text-slate-600 px-1"
        >
          ⋮⋮
        </button>
        <span className="text-xs font-medium text-slate-600 flex-1">
          {element.type === 'custom'
            ? element.customLabel || element.customTag || 'Custom'
            : element.type}
        </span>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-slate-400 hover:text-slate-600"
        >
          {expanded ? '▼' : '▶'}
        </button>
        <button onClick={onRemove} className="text-red-400 hover:text-red-600 text-xs">
          ✕
        </button>
      </div>

      {expanded && (
        <div className="px-3 pb-3 space-y-2 border-t border-slate-200 pt-2">
          <div>
            <label className="text-xs text-slate-400">Text Value</label>
            <textarea
              value={element.value}
              onChange={(e) => onUpdate({ value: e.target.value })}
              rows={2}
              className="w-full border border-slate-300 rounded px-2 py-1 text-xs"
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs text-slate-400">Font Family</label>
              <select
                value={element.fontFamily}
                onChange={(e) => onUpdate({ fontFamily: e.target.value })}
                className="w-full border border-slate-300 rounded px-2 py-1 text-xs"
              >
                {FONT_FAMILIES.map((f) => (
                  <option key={f} value={f}>
                    {f}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-400">Font Size</label>
              <input
                type="number"
                min={6}
                max={120}
                value={element.fontSize}
                onChange={(e) => onUpdate({ fontSize: Number(e.target.value) })}
                className="w-full border border-slate-300 rounded px-2 py-1 text-xs"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400">Font Weight</label>
              <select
                value={element.fontWeight}
                onChange={(e) => onUpdate({ fontWeight: Number(e.target.value) })}
                className="w-full border border-slate-300 rounded px-2 py-1 text-xs"
              >
                {FONT_WEIGHTS.map((w) => (
                  <option key={w} value={w}>
                    {w}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-400">Style</label>
              <select
                value={element.fontStyle}
                onChange={(e) =>
                  onUpdate({ fontStyle: e.target.value as 'normal' | 'italic' })
                }
                className="w-full border border-slate-300 rounded px-2 py-1 text-xs"
              >
                <option value="normal">Normal</option>
                <option value="italic">Italic</option>
              </select>
            </div>
            <div className="col-span-2">
              <label className="text-xs text-slate-400">Color</label>
              <div className="flex gap-2">
                <input
                  type="color"
                  value={element.fontColor}
                  onChange={(e) => onUpdate({ fontColor: e.target.value })}
                  className="w-8 h-8 rounded border border-slate-300 cursor-pointer"
                />
                <input
                  type="text"
                  value={element.fontColor}
                  onChange={(e) => onUpdate({ fontColor: e.target.value })}
                  className="flex-1 border border-slate-300 rounded px-2 py-1 text-xs uppercase"
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
