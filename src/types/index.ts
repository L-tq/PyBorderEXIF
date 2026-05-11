export interface BorderConfig {
  strategy: 'custom' | 'fixed-aspect-ratio';
  top: number;
  bottom: number;
  left: number;
  right: number;
  color: string;
  fixedParam?: 'a' | 'b' | 'c';
}

export interface LogoConfig {
  id: string;
  dataUrl: string;
  fileName: string;
  relX: number;
  relY: number;
  offsetX: number;
  offsetY: number;
  scale: number;
  originalWidth: number;
  originalHeight: number;
}

export type TextElementType =
  | 'author'
  | 'camera'
  | 'lens'
  | 'focal-length'
  | 'aperture'
  | 'iso'
  | 'custom';

export interface TextElementConfig {
  id: string;
  type: TextElementType;
  customTag?: string;
  customLabel?: string;
  value: string;
  order: number;
  fontFamily: string;
  fontSize: number;
  fontColor: string;
  fontWeight: number;
  fontStyle: 'normal' | 'italic';
}

export interface TextLayout {
  leftMargin: number;
  rightMargin: number;
  bottomMargin: number;
  lineSpacing: number;
}

export interface ImageConfig {
  id: string;
  file: File;
  dataUrl: string;
  exif: Record<string, unknown>;
  width: number;
  height: number;
  border: BorderConfig;
  logos: LogoConfig[];
  textElements: TextElementConfig[];
  textLayout: TextLayout;
}

export interface AppState {
  images: ImageConfig[];
  activeImageIndex: number;
  step: 1 | 2 | 3;
}

export type AppAction =
  | { type: 'SET_IMAGES'; payload: ImageConfig[] }
  | { type: 'ADD_IMAGES'; payload: ImageConfig[] }
  | { type: 'REMOVE_IMAGE'; payload: string }
  | { type: 'SET_ACTIVE_IMAGE'; payload: number }
  | { type: 'SET_STEP'; payload: 1 | 2 | 3 }
  | { type: 'UPDATE_BORDER'; payload: { imageId: string; border: Partial<BorderConfig> } }
  | { type: 'ADD_LOGO'; payload: { imageId: string; logo: LogoConfig } }
  | { type: 'REMOVE_LOGO'; payload: { imageId: string; logoId: string } }
  | { type: 'UPDATE_LOGO'; payload: { imageId: string; logoId: string; updates: Partial<LogoConfig> } }
  | { type: 'ADD_TEXT_ELEMENT'; payload: { imageId: string; element: TextElementConfig } }
  | { type: 'REMOVE_TEXT_ELEMENT'; payload: { imageId: string; elementId: string } }
  | { type: 'UPDATE_TEXT_ELEMENT'; payload: { imageId: string; elementId: string; updates: Partial<TextElementConfig> } }
  | { type: 'REORDER_TEXT_ELEMENTS'; payload: { imageId: string; elements: TextElementConfig[] } }
  | { type: 'UPDATE_TEXT_LAYOUT'; payload: { imageId: string; layout: Partial<TextLayout> } }
  | { type: 'UPDATE_IMAGE_EXIF'; payload: { imageId: string; exif: Record<string, unknown> } };
