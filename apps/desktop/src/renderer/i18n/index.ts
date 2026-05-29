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

import { genEn, genEs, genFr, genDe, genJa, genZh } from './catalog.generated';

export type Locale = 'en' | 'es' | 'fr' | 'de' | 'ja' | 'zh';

export const LOCALES: { code: Locale; label: string; flag: string }[] = [
  { code: 'en', label: 'English', flag: '🇬🇧' },
  { code: 'es', label: 'Español', flag: '🇪🇸' },
  { code: 'fr', label: 'Français', flag: '🇫🇷' },
  { code: 'de', label: 'Deutsch', flag: '🇩🇪' },
  { code: 'ja', label: '日本語', flag: '🇯🇵' },
  { code: 'zh', label: '中文 (简体)', flag: '🇨🇳' },
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

// French — full locale: nav/common (hand-authored) + generated page-body keys.
const fr: Catalog = {
  ...genFr,
  'nav.projects': 'Projets',
  'nav.analytics': 'Analytique',
  'nav.explainability': 'Explicabilité',
  'nav.archive': 'Archives',
  'nav.settings': 'Paramètres',
  'nav.systemHealth': 'État du système',
  'nav.help': 'Aide',
  'nav.search': 'Rechercher',
  'nav.shortcuts': 'Raccourcis',
  'common.save': 'Enregistrer',
  'common.cancel': 'Annuler',
  'common.export': 'Exporter',
  'common.delete': 'Supprimer',
  'common.newProject': 'Nouveau projet',
  'common.refresh': 'Actualiser',
  'common.language': 'Langue',
};

// German — full locale: nav/common (hand-authored) + generated page-body keys.
const de: Catalog = {
  ...genDe,
  'nav.projects': 'Projekte',
  'nav.analytics': 'Analytik',
  'nav.explainability': 'Erklärbarkeit',
  'nav.archive': 'Archiv',
  'nav.settings': 'Einstellungen',
  'nav.systemHealth': 'Systemstatus',
  'nav.help': 'Hilfe',
  'nav.search': 'Suchen',
  'nav.shortcuts': 'Tastenkürzel',
  'common.save': 'Speichern',
  'common.cancel': 'Abbrechen',
  'common.export': 'Exportieren',
  'common.delete': 'Löschen',
  'common.newProject': 'Neues Projekt',
  'common.refresh': 'Aktualisieren',
  'common.language': 'Sprache',
};

// Japanese — full locale: nav/common (hand-authored) + generated page-body keys.
const ja: Catalog = {
  ...genJa,
  'nav.projects': 'プロジェクト',
  'nav.analytics': '分析',
  'nav.explainability': '説明可能性',
  'nav.archive': 'アーカイブ',
  'nav.settings': '設定',
  'nav.systemHealth': 'システム状態',
  'nav.help': 'ヘルプ',
  'nav.search': '検索',
  'nav.shortcuts': 'ショートカット',
  'common.save': '保存',
  'common.cancel': 'キャンセル',
  'common.export': 'エクスポート',
  'common.delete': '削除',
  'common.newProject': '新規プロジェクト',
  'common.refresh': '更新',
  'common.language': '言語',
};

// Simplified Chinese — full locale: nav/common (hand-authored) + generated keys.
const zh: Catalog = {
  ...genZh,
  'nav.projects': '项目',
  'nav.analytics': '分析',
  'nav.explainability': '可解释性',
  'nav.archive': '归档',
  'nav.settings': '设置',
  'nav.systemHealth': '系统状态',
  'nav.help': '帮助',
  'nav.search': '搜索',
  'nav.shortcuts': '快捷键',
  'common.save': '保存',
  'common.cancel': '取消',
  'common.export': '导出',
  'common.delete': '删除',
  'common.newProject': '新建项目',
  'common.refresh': '刷新',
  'common.language': '语言',
};

const catalogs: Record<Locale, Catalog> = { en, es, fr, de, ja, zh };

/** Resolve a translation key for a locale, falling back to English then the key. */
export function translate(locale: Locale, key: string, fallback?: string): string {
  return catalogs[locale]?.[key] ?? en[key] ?? fallback ?? key;
}

/** Total translatable keys in the catalog (for coverage reporting/tests). */
export const CATALOG_KEYS = Object.keys(en);

const SUPPORTED = new Set<Locale>(LOCALES.map((l) => l.code));

/**
 * Map a BCP-47 language tag (e.g. 'ja-JP', 'zh-CN', 'pt-BR') to a supported
 * Locale by its primary subtag, or null if unsupported. We ship one Chinese
 * (Simplified), so any 'zh*' maps to 'zh'.
 */
export function matchLocale(tag: string | undefined | null): Locale | null {
  if (!tag) return null;
  const base = tag.toLowerCase().split('-')[0];
  return SUPPORTED.has(base as Locale) ? (base as Locale) : null;
}

/**
 * Detect the best supported locale from the browser/OS languages, for first
 * launch (before the user has explicitly chosen). Falls back to DEFAULT_LOCALE.
 * International-launch UX: a German/Japanese/… user sees their language by
 * default instead of always English. An explicit choice (persisted) overrides.
 */
export function detectLocale(): Locale {
  try {
    const nav = typeof navigator !== 'undefined' ? navigator : undefined;
    const candidates: (string | undefined)[] = [
      ...(nav?.languages ?? []),
      nav?.language,
    ];
    for (const tag of candidates) {
      const m = matchLocale(tag);
      if (m) return m;
    }
  } catch {
    /* non-browser env */
  }
  return DEFAULT_LOCALE;
}
