import Cookies from 'js-cookie';
import type { BorderConfig, TextLayout, TextElementConfig } from '../types';

const COOKIE_KEY = 'borderexif-settings';
const COOKIE_OPTIONS = { expires: 365, sameSite: 'strict' as const };

interface PersistedSettings {
  border: Partial<BorderConfig>;
  textLayout: Partial<TextLayout>;
  textElements: Partial<TextElementConfig>[];
  defaultAuthor: string;
}

export function saveSettings(
  border: BorderConfig,
  textLayout: TextLayout,
  textElements: TextElementConfig[],
  defaultAuthor: string
): void {
  const data: PersistedSettings = {
    border: {
      strategy: border.strategy,
      top: border.top,
      bottom: border.bottom,
      left: border.left,
      right: border.right,
      color: border.color,
      fixedParam: border.fixedParam,
    },
    textLayout: { ...textLayout },
    textElements: textElements.map((el) => ({
      type: el.type,
      fontFamily: el.fontFamily,
      fontSize: el.fontSize,
      fontColor: el.fontColor,
      fontWeight: el.fontWeight,
      fontStyle: el.fontStyle,
    })),
    defaultAuthor,
  };
  Cookies.set(COOKIE_KEY, JSON.stringify(data), COOKIE_OPTIONS);
}

export function loadSettings(): PersistedSettings | null {
  const raw = Cookies.get(COOKIE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as PersistedSettings;
  } catch {
    return null;
  }
}
