/**
 * Application routes configuration.
 */

import { RouteObject } from 'react-router-dom';
import { MainLayout } from './layouts/main-layout';
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

export const routes: RouteObject[] = [
  {
    path: '/',
    element: <MainLayout />,
    children: [
      {
        index: true,
        element: <HomePage />,
      },
      {
        path: 'project/:projectId',
        element: <ProjectPage />,
      },
      {
        path: 'project/:projectId/characters',
        element: <CharacterLabPage />,
      },
      {
        path: 'project/:projectId/scenes',
        element: <ScenePlanningPage />,
      },
      {
        path: 'project/:projectId/generate',
        element: <GenerationPage />,
      },
      {
        path: 'project/:projectId/timeline',
        element: <TimelinePage />,
      },
      {
        path: 'project/:projectId/export',
        element: <ExportPage />,
      },
      {
        path: 'analytics',
        element: <AnalyticsPage />,
      },
      {
        path: 'settings',
        element: <SettingsPage />,
      },
      {
        path: 'archive',
        element: <ArchivePage />,
      },
      {
        path: 'help',
        element: <HelpPage />,
      },
      {
        path: 'admin',
        element: <AdminPage />,
      },
      {
        path: 'actforge',
        element: <ActForgePage />,
      },
      {
        path: 'project/:projectId/actforge',
        element: <ActForgePage />,
      },
      {
        path: 'dna-strand-demo',
        element: <DnaStrandDemoPage />,
      },
      {
        path: 'explainability',
        element: <ExplainabilityPage />,
      },
      {
        path: 'project/:projectId/explainability',
        element: <ExplainabilityPage />,
      },
    ],
  },
];
