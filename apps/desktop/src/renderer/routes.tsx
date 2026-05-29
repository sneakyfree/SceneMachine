/**
 * Application routes configuration.
 *
 * Each route's element is wrapped in `PageErrorBoundary` so a crash on
 * one page can't take down the entire renderer (which is what React
 * Router's default ErrorBoundary did — bare stack traces, no recovery).
 *
 * Iter 12 fixed 8 specific crash sites that took down 9 of 17 pages.
 * This iter (20) adds the defense-in-depth so the NEXT crash — from
 * code that doesn't exist yet — only kills its own route. The user
 * gets a "Page Error" card with a reload button while the rest of
 * the app (sidebar nav, Steven assistant, toasts) keeps working.
 */

import type { ReactElement } from 'react';
import { RouteObject } from 'react-router-dom';
import { MainLayout } from './layouts/main-layout';
import { PageErrorBoundary } from './components/error-boundary';
import { HomePage } from './pages/home';
import { ProjectPage } from './pages/project';
import { CharacterLabPage } from './pages/character-lab';
import { ScenePlanningPage } from './pages/scene-planning';
import { GenerationPage } from './pages/generation';
import { ExportPage } from './pages/export';
import { SettingsPage } from './pages/settings';
import { AnalyticsPage } from './pages/analytics';
import { TimelinePage } from './pages/timeline';
import { HelpPage } from './pages/help';
import { ArchivePage } from './pages/archive';
import { AdminPage } from './pages/admin';
import { ActForgePage } from './pages/actforge';
import { DnaStrandDemoPage } from './pages/dna-strand-demo';
import { ExplainabilityPage } from './pages/explainability';
import { NotFoundPage } from './pages/not-found';

/** Wrap a page element in PageErrorBoundary. Centralized so every route
 *  gets the same recovery UX without bloating each route entry. */
function guarded(page: ReactElement): ReactElement {
  return <PageErrorBoundary>{page}</PageErrorBoundary>;
}

export const routes: RouteObject[] = [
  {
    path: '/',
    element: <MainLayout />,
    children: [
      {
        index: true,
        element: guarded(<HomePage />),
      },
      {
        path: 'project/:projectId',
        element: guarded(<ProjectPage />),
      },
      {
        path: 'project/:projectId/characters',
        element: guarded(<CharacterLabPage />),
      },
      {
        path: 'project/:projectId/scenes',
        element: guarded(<ScenePlanningPage />),
      },
      {
        path: 'project/:projectId/generate',
        element: guarded(<GenerationPage />),
      },
      {
        path: 'project/:projectId/timeline',
        element: guarded(<TimelinePage />),
      },
      {
        path: 'project/:projectId/export',
        element: guarded(<ExportPage />),
      },
      {
        path: 'analytics',
        element: guarded(<AnalyticsPage />),
      },
      {
        path: 'settings',
        element: guarded(<SettingsPage />),
      },
      {
        path: 'archive',
        element: guarded(<ArchivePage />),
      },
      {
        path: 'help',
        element: guarded(<HelpPage />),
      },
      {
        path: 'admin',
        element: guarded(<AdminPage />),
      },
      {
        path: 'actforge',
        element: guarded(<ActForgePage />),
      },
      {
        path: 'project/:projectId/actforge',
        element: guarded(<ActForgePage />),
      },
      {
        path: 'dna-strand-demo',
        element: guarded(<DnaStrandDemoPage />),
      },
      {
        path: 'explainability',
        element: guarded(<ExplainabilityPage />),
      },
      {
        path: 'project/:projectId/explainability',
        element: guarded(<ExplainabilityPage />),
      },
      {
        // Catch-all: any unmatched URL renders the friendly NotFound page
        // (inside MainLayout, so the sidebar nav stays usable) instead of
        // React Router's raw "Unexpected Application Error! 404" screen.
        path: '*',
        element: guarded(<NotFoundPage />),
      },
    ],
  },
];
