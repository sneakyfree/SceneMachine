/**
 * Breadcrumbs component.
 *
 * Provides hierarchical navigation showing the current page location
 * within the application. Helps users understand where they are and
 * navigate back to parent pages.
 */

import { useMemo } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Home,
  Film,
  Users,
  Clapperboard,
  Wand2,
  Download,
  ChevronRight,
  Settings,
  BarChart3,
  HelpCircle,
} from 'lucide-react';
import { cn } from '../lib/utils';

interface BreadcrumbItem {
  label: string;
  href?: string;
  icon?: React.ReactNode;
}

interface BreadcrumbsProps {
  className?: string;
}

export function Breadcrumbs({ className }: BreadcrumbsProps) {
  const location = useLocation();
  const { projectId } = useParams<{ projectId?: string }>();

  // Fetch project name if we're on a project page
  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: async () => {
      if (!projectId) return null;
      const result = await window.electronAPI.backendRequest<{ name: string }>(
        'projects.get',
        { project_id: projectId }
      );
      return result;
    },
    enabled: !!projectId,
    staleTime: 60 * 1000,
  });

  const items = useMemo(() => {
    const crumbs: BreadcrumbItem[] = [];
    const path = location.pathname;

    // Always start with Projects/Home
    crumbs.push({
      label: 'Projects',
      href: '/',
      icon: <Home className="w-4 h-4" />,
    });

    // Settings page
    if (path === '/settings') {
      crumbs.push({
        label: 'Settings',
        icon: <Settings className="w-4 h-4" />,
      });
      return crumbs;
    }

    // Analytics page
    if (path === '/analytics') {
      crumbs.push({
        label: 'Analytics',
        icon: <BarChart3 className="w-4 h-4" />,
      });
      return crumbs;
    }

    // Help page
    if (path === '/help') {
      crumbs.push({
        label: 'Help',
        icon: <HelpCircle className="w-4 h-4" />,
      });
      return crumbs;
    }

    // If on a project page
    if (projectId) {
      crumbs.push({
        label: project?.name || 'Loading...',
        href: `/project/${projectId}`,
        icon: <Film className="w-4 h-4" />,
      });

      // Sub-page detection
      if (path.includes('/characters')) {
        crumbs.push({
          label: 'Character Lab',
          icon: <Users className="w-4 h-4" />,
        });
      } else if (path.includes('/scenes')) {
        crumbs.push({
          label: 'Scene Planning',
          icon: <Clapperboard className="w-4 h-4" />,
        });
      } else if (path.includes('/generate')) {
        crumbs.push({
          label: 'Generation',
          icon: <Wand2 className="w-4 h-4" />,
        });
      } else if (path.includes('/export')) {
        crumbs.push({
          label: 'Export',
          icon: <Download className="w-4 h-4" />,
        });
      }
    }

    return crumbs;
  }, [location.pathname, projectId, project?.name]);

  // Don't show breadcrumbs on home page
  if (items.length <= 1) {
    return null;
  }

  return (
    <nav
      aria-label="Breadcrumb navigation"
      className={cn('flex items-center gap-1 text-sm', className)}
    >
      <ol className="flex items-center gap-1" role="list">
        {items.map((item, index) => {
          const isLast = index === items.length - 1;

          return (
            <li key={index} className="flex items-center gap-1">
              {index > 0 && (
                <ChevronRight
                  className="w-4 h-4 text-surface-500 shrink-0"
                  aria-hidden="true"
                />
              )}

              {item.href && !isLast ? (
                <Link
                  to={item.href}
                  className="flex items-center gap-1.5 text-surface-400 hover:text-surface-200 transition-colors px-1.5 py-1 rounded hover:bg-surface-800"
                >
                  {item.icon && (
                    <span className="shrink-0" aria-hidden="true">
                      {item.icon}
                    </span>
                  )}
                  <span className="truncate max-w-[150px]">{item.label}</span>
                </Link>
              ) : (
                <span
                  className={cn(
                    'flex items-center gap-1.5 px-1.5 py-1',
                    isLast
                      ? 'text-surface-100 font-medium'
                      : 'text-surface-400'
                  )}
                  aria-current={isLast ? 'page' : undefined}
                >
                  {item.icon && (
                    <span className="shrink-0" aria-hidden="true">
                      {item.icon}
                    </span>
                  )}
                  <span className="truncate max-w-[200px]">{item.label}</span>
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
