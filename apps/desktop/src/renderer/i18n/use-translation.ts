/**
 * useTranslation — the hook components call to localize strings.
 *
 *   const { t, locale, setLocale } = useTranslation();
 *   <span>{t('nav.projects')}</span>
 *
 * `t(key, fallback?)` resolves against the active locale, falling back to
 * English then the key. Reads the persisted locale from the experience store.
 */

import { useCallback } from 'react';

import { useExperienceStore } from '../stores/experience-store';
import { type Locale, translate } from './index';

export function useTranslation() {
  const locale = useExperienceStore((s) => s.locale);
  const setLocale = useExperienceStore((s) => s.setLocale);

  const t = useCallback(
    (key: string, fallback?: string) => translate(locale, key, fallback),
    [locale],
  );

  return { t, locale, setLocale } as { t: (key: string, fallback?: string) => string; locale: Locale; setLocale: (l: Locale) => void };
}
