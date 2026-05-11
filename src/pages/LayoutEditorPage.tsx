import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppState, useActiveImage } from '../context/AppContext';
import BorderConfigPanel from '../components/BorderConfig';
import LogoManager from '../components/LogoManager';
import TextEditor from '../components/TextEditor';
import PreviewCanvas from '../components/PreviewCanvas';

type Panel = 'border' | 'logos' | 'text';

interface Props {
  authorName: string;
  onAuthorChange: (name: string) => void;
}

export default function LayoutEditorPage({ authorName, onAuthorChange }: Props) {
  const { state, dispatch } = useAppState();
  const image = useActiveImage();
  const navigate = useNavigate();
  const [expandedPanel, setExpandedPanel] = useState<Panel>('border');

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

  const panelConfigs: { key: Panel; label: string; icon: string }[] = [
    { key: 'border', label: 'Border', icon: '⬜' },
    { key: 'logos', label: 'Logos', icon: '🖼' },
    { key: 'text', label: 'Text', icon: '📝' },
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-80px)]">
      <div className="flex items-center justify-between px-6 py-3 bg-white border-b border-slate-200">
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-bold text-slate-800">
            Step 2: Layout & Preview
          </h1>
          {state.images.length > 1 && (
            <div className="flex items-center gap-1">
              {state.images.map((img, i) => (
                <button
                  key={img.id}
                  onClick={() => dispatch({ type: 'SET_ACTIVE_IMAGE', payload: i })}
                  className={`px-2 py-1 text-xs rounded ${
                    i === state.activeImageIndex
                      ? 'bg-blue-500 text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {img.file.name.slice(0, 12)}
                  {img.file.name.length > 12 ? '…' : ''}
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => {
              dispatch({ type: 'SET_STEP', payload: 1 });
              navigate('/');
            }}
            className="px-4 py-2 text-sm text-slate-600 hover:text-slate-800"
          >
            ← Back
          </button>
          <button
            onClick={() => {
              dispatch({ type: 'SET_STEP', payload: 3 });
              navigate('/review');
            }}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg text-sm font-medium hover:bg-blue-600"
          >
            Next: Review & Download →
          </button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <div className="w-80 bg-white border-r border-slate-200 overflow-y-auto flex-shrink-0">
          <div className="p-4 space-y-4">
            <div className="flex gap-1">
              {panelConfigs.map((panel) => (
                <button
                  key={panel.key}
                  onClick={() => setExpandedPanel(panel.key)}
                  className={`flex-1 px-2 py-2 text-xs font-medium rounded-lg transition-colors ${
                    expandedPanel === panel.key
                      ? 'bg-blue-500 text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {panel.icon} {panel.label}
                </button>
              ))}
            </div>

            {expandedPanel === 'border' && (
              <BorderConfigPanel border={image.border} imageId={image.id} />
            )}

            {expandedPanel === 'logos' && (
              <LogoManager logos={image.logos} imageId={image.id} />
            )}

            {expandedPanel === 'text' && (
              <TextEditor
                elements={image.textElements}
                layout={image.textLayout}
                imageId={image.id}
                exif={image.exif}
                authorName={authorName}
                onAuthorChange={onAuthorChange}
              />
            )}
          </div>
        </div>

        {/* Preview */}
        <div className="flex-1 overflow-auto p-6 bg-slate-50">
          <PreviewCanvas image={image} />
        </div>
      </div>
    </div>
  );
}
