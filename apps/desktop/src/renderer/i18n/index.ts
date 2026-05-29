/**
 * Lightweight, dependency-free i18n foundation.
 *
 * International-launch readiness: a typed string catalog keyed by locale, with
 * English as the source/fallback. `translate(locale, key)` resolves a key to
 * the active locale, falling back to English, then to the key/fallback — so a
 * missing translation degrades gracefully instead of showing a blank.
 *
 * This is the foundation + pattern: the global navigation and common UI are
 * translated here as the proof. Remaining hardcoded strings across the pages
 * migrate to `t('...')` keys incrementally (see docs/INVENTORY_DEFECTS.md
 * "i18n migration"). Adding a locale = adding one catalog object below.
 */

import { genEn, genEs } from './catalog.generated';

export type Locale = 'en' | 'es';

export const LOCALES: { code: Locale; label: string; flag: string }[] = [
  { code: 'en', label: 'English', flag: '🇬🇧' },
  { code: 'es', label: 'Español', flag: '🇪🇸' },
];

export const DEFAULT_LOCALE: Locale = 'en';

type Catalog = Record<string, string>;

// English — the source of truth. Every key MUST exist here (fallback target).
// Hand-authored nav/common keys first, then the generated page-body catalog.
const en: Catalog = {
  ...genEn,
  // Global navigation (rendered on every page)
  'nav.projects': 'Projects',
  'nav.analytics': 'Analytics',
  'nav.explainability': 'Explainability',
  'nav.archive': 'Archive',
  'nav.settings': 'Settings',
  'nav.systemHealth': 'System Health',
  'nav.help': 'Help',
  'nav.search': 'Search',
  'nav.shortcuts': 'Shortcuts',
  // Common actions
  'common.save': 'Save',
  'common.cancel': 'Cancel',
  'common.export': 'Export',
  'common.delete': 'Delete',
  'common.newProject': 'New Project',
  'common.refresh': 'Refresh',
  'common.language': 'Language',
};

// Spanish — full locale: nav/common (hand-authored) + generated page-body keys.
const es: Catalog = {
  ...genEs,
  'nav.projects': 'Proyectos',
  'nav.analytics': 'Analíticas',
  'nav.explainability': 'Explicabilidad',
  'nav.archive': 'Archivo',
  'nav.settings': 'Configuración',
  'nav.systemHealth': 'Estado del Sistema',
  'nav.help': 'Ayuda',
  'nav.search': 'Buscar',
  'nav.shortcuts': 'Atajos',
  'common.save': 'Guardar',
  'common.cancel': 'Cancelar',
  'common.export': 'Exportar',
  'common.delete': 'Eliminar',
  'common.newProject': 'Nuevo Proyecto',
  'common.refresh': 'Actualizar',
  'common.language': 'Idioma',
};

const catalogs: Record<Locale, Catalog> = { en, es };

/** Resolve a translation key for a locale, falling back to English then the key. */
export function translate(locale: Locale, key: string, fallback?: string): string {
  return catalogs[locale]?.[key] ?? en[key] ?? fallback ?? key;
}

/** Total translatable keys in the catalog (for coverage reporting/tests). */
export const CATALOG_KEYS = Object.keys(en);
