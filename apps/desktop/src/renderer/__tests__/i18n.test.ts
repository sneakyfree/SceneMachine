import { describe, it, expect } from 'vitest';
import { translate, LOCALES, CATALOG_KEYS, DEFAULT_LOCALE } from '../i18n';

describe('i18n catalog', () => {
  it('every locale translates every English key (no silent EN fallback)', () => {
    for (const { code } of LOCALES) {
      for (const key of CATALOG_KEYS) {
        const val = translate(code, key);
        expect(val, `${code} missing "${key}"`).toBeTruthy();
        // Non-English locales must NOT just echo the English string for nav keys.
        if (code !== 'en' && key.startsWith('nav.')) {
          expect(val, `${code} "${key}" not translated`).not.toBe(translate('en', key));
        }
      }
    }
  });

  it('falls back EN→key when a translation is missing', () => {
    expect(translate('es', 'nav.projects')).toBe('Proyectos');
    expect(translate('es', 'does.not.exist')).toBe('does.not.exist');
    expect(translate('es', 'does.not.exist', 'Fallback')).toBe('Fallback');
  });

  it('default locale is English', () => {
    expect(DEFAULT_LOCALE).toBe('en');
    expect(translate(DEFAULT_LOCALE, 'common.save')).toBe('Save');
  });
});
