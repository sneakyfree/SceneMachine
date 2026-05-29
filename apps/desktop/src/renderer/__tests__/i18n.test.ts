import { describe, it, expect } from 'vitest';
import { translate, LOCALES, CATALOG_KEYS, DEFAULT_LOCALE, matchLocale } from '../i18n';

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

  it('matchLocale maps BCP-47 tags to supported locales (or null)', () => {
    expect(matchLocale('ja-JP')).toBe('ja');
    expect(matchLocale('zh-CN')).toBe('zh'); // Simplified is the only Chinese we ship
    expect(matchLocale('zh-Hant-TW')).toBe('zh');
    expect(matchLocale('de-AT')).toBe('de');
    expect(matchLocale('fr-CA')).toBe('fr');
    expect(matchLocale('es-419')).toBe('es');
    expect(matchLocale('en-GB')).toBe('en');
    expect(matchLocale('pt-BR')).toBeNull(); // unsupported → caller falls back to en
    expect(matchLocale('it')).toBeNull();
    expect(matchLocale(undefined)).toBeNull();
    expect(matchLocale('')).toBeNull();
  });
});
