import { createContext, useContext, useReducer, type Dispatch } from 'react';
import type { AppState, AppAction, ImageConfig } from '../types';

function createDefaultState(): AppState {
  return {
    images: [],
    activeImageIndex: 0,
    step: 1,
  };
}

function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case 'SET_IMAGES':
      return { ...state, images: action.payload, activeImageIndex: 0 };

    case 'ADD_IMAGES':
      return {
        ...state,
        images: [...state.images, ...action.payload],
        activeImageIndex: state.images.length,
      };

    case 'REMOVE_IMAGE': {
      const images = state.images.filter((img) => img.id !== action.payload);
      const activeIndex = Math.min(state.activeImageIndex, images.length - 1);
      return { ...state, images, activeImageIndex: Math.max(0, activeIndex) };
    }

    case 'SET_ACTIVE_IMAGE':
      return { ...state, activeImageIndex: action.payload };

    case 'SET_STEP':
      return { ...state, step: action.payload };

    case 'UPDATE_BORDER': {
      const images = state.images.map((img) =>
        img.id === action.payload.imageId
          ? { ...img, border: { ...img.border, ...action.payload.border } }
          : img
      );
      return { ...state, images };
    }

    case 'ADD_LOGO': {
      const images = state.images.map((img) =>
        img.id === action.payload.imageId
          ? { ...img, logos: [...img.logos, action.payload.logo] }
          : img
      );
      return { ...state, images };
    }

    case 'REMOVE_LOGO': {
      const images = state.images.map((img) =>
        img.id === action.payload.imageId
          ? { ...img, logos: img.logos.filter((l) => l.id !== action.payload.logoId) }
          : img
      );
      return { ...state, images };
    }

    case 'UPDATE_LOGO': {
      const images = state.images.map((img) =>
        img.id === action.payload.imageId
          ? {
              ...img,
              logos: img.logos.map((l) =>
                l.id === action.payload.logoId
                  ? { ...l, ...action.payload.updates }
                  : l
              ),
            }
          : img
      );
      return { ...state, images };
    }

    case 'ADD_TEXT_ELEMENT': {
      const images = state.images.map((img) =>
        img.id === action.payload.imageId
          ? { ...img, textElements: [...img.textElements, action.payload.element] }
          : img
      );
      return { ...state, images };
    }

    case 'REMOVE_TEXT_ELEMENT': {
      const images = state.images.map((img) =>
        img.id === action.payload.imageId
          ? {
              ...img,
              textElements: img.textElements.filter(
                (el) => el.id !== action.payload.elementId
              ),
            }
          : img
      );
      return { ...state, images };
    }

    case 'UPDATE_TEXT_ELEMENT': {
      const images = state.images.map((img) =>
        img.id === action.payload.imageId
          ? {
              ...img,
              textElements: img.textElements.map((el) =>
                el.id === action.payload.elementId
                  ? { ...el, ...action.payload.updates }
                  : el
              ),
            }
          : img
      );
      return { ...state, images };
    }

    case 'REORDER_TEXT_ELEMENTS': {
      const images = state.images.map((img) =>
        img.id === action.payload.imageId
          ? { ...img, textElements: action.payload.elements }
          : img
      );
      return { ...state, images };
    }

    case 'UPDATE_TEXT_LAYOUT': {
      const images = state.images.map((img) =>
        img.id === action.payload.imageId
          ? { ...img, textLayout: { ...img.textLayout, ...action.payload.layout } }
          : img
      );
      return { ...state, images };
    }

    case 'UPDATE_IMAGE_EXIF': {
      const images = state.images.map((img) =>
        img.id === action.payload.imageId
          ? { ...img, exif: action.payload.exif }
          : img
      );
      return { ...state, images };
    }

    default:
      return state;
  }
}

interface AppContextValue {
  state: AppState;
  dispatch: Dispatch<AppAction>;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, null, createDefaultState);
  return (
    <AppContext.Provider value={{ state, dispatch }}>
      {children}
    </AppContext.Provider>
  );
}

export function useAppState() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useAppState must be used within AppProvider');
  return ctx;
}

export function useActiveImage(): ImageConfig | undefined {
  const { state } = useAppState();
  return state.images[state.activeImageIndex];
}
