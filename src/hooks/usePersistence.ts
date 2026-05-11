import { useEffect, useRef } from 'react';
import { useAppState } from '../context/AppContext';
import { saveSettings, loadSettings } from '../utils/cookies';

export function usePersistence(defaultAuthor: string) {
  const { state, dispatch } = useAppState();
  const loadedRef = useRef(false);

  // Load persisted settings on mount
  useEffect(() => {
    if (loadedRef.current) return;
    loadedRef.current = true;

    const saved = loadSettings();
    if (!saved) return;

    // Apply saved defaults to each image's border and text layout
    if (state.images.length > 0) {
      for (const img of state.images) {
        if (saved.border) {
          dispatch({
            type: 'UPDATE_BORDER',
            payload: { imageId: img.id, border: saved.border },
          });
        }
        if (saved.textLayout) {
          dispatch({
            type: 'UPDATE_TEXT_LAYOUT',
            payload: { imageId: img.id, layout: saved.textLayout },
          });
        }
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.images.length > 0]);

  // Save settings when they change
  useEffect(() => {
    const activeImage = state.images[state.activeImageIndex];
    if (!activeImage) return;

    const timer = setTimeout(() => {
      saveSettings(
        activeImage.border,
        activeImage.textLayout,
        activeImage.textElements,
        defaultAuthor
      );
    }, 1000);

    return () => clearTimeout(timer);
  }, [
    state.images,
    state.activeImageIndex,
    defaultAuthor,
  ]);
}
