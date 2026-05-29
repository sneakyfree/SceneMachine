/**
 * 404 / unmatched-route page.
 *
 * React Router's default behavior for an unmatched path is to render its
 * built-in error element — a bare "Unexpected Application Error! 404 Not
 * Found / Hey developer 👋 ..." message that leaks developer-facing copy to
 * end users (caught by the QA screenshot tour, 2026-05-28).
 *
 * The PageErrorBoundary wrappers in routes.tsx only catch crashes *inside* a
 * matched route's element — an unmatched URL never mounts an element, so the
 * boundary can't help. This catch-all route closes that gap: any mistyped
 * link, stale bookmark, or programmatic mis-navigation lands here with the
 * sidebar nav intact and a clear way back, instead of a raw stack-trace-style
 * screen.
 */

import { useRouteError, isRouteErrorResponse } from 'react-router-dom';
import { Link, useNavigate } from 'react-router-dom';
import { Compass, ArrowLeft, Home } from 'lucide-react';
import { useTranslation } from '../i18n/use-translation';

export function NotFoundPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  // When this element is used as a route's `errorElement`, useRouteError gives
  // us the thrown response (e.g. a 404). When it's the matched element for a
  // catch-all `path: '*'` route, there is no error and this is null — both
  // paths render the same friendly page.
  const error = useRouteError();

  const statusText = isRouteErrorResponse(error)
    ? `${error.status} ${error.statusText}`
    : t('notFound.statusText', 'Page not found');

  return (
    <div className="flex flex-col items-center justify-center h-full p-8 text-center">
      <Compass className="w-14 h-14 text-brand-400 mb-4" />
      <h2 className="text-2xl font-bold mb-1">{t('notFound.heading', 'This page took a wrong turn')}</h2>
      <p className="text-surface-400 mb-1">{statusText}</p>
      <p className="text-surface-400 max-w-md mb-6">
        {t(
          'notFound.description',
          "The page you're looking for doesn't exist or may have moved. Check the address, or head back to your projects.",
        )}
      </p>
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate(-1)}
          className="px-4 py-2 bg-surface-800 hover:bg-surface-700 rounded-lg flex items-center gap-2"
        >
          <ArrowLeft className="w-4 h-4" />
          {t('notFound.goBack', 'Go Back')}
        </button>
        <Link
          to="/"
          className="px-4 py-2 bg-brand-500 hover:bg-brand-600 rounded-lg flex items-center gap-2"
        >
          <Home className="w-4 h-4" />
          {t('notFound.backToProjects', 'Back to Projects')}
        </Link>
      </div>
    </div>
  );
}
