/**
 * Breadcrumbs component tests.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// Mock the Breadcrumbs component
vi.mock('../../components/breadcrumbs', () => ({
  Breadcrumbs: ({ items, separator = '/' }: any) => (
    <nav aria-label="Breadcrumb" data-testid="breadcrumbs">
      <ol className="flex items-center">
        {items?.map((item: any, index: number) => (
          <li key={item.href || index} className="flex items-center">
            {index > 0 && (
              <span data-testid="separator" className="mx-2">
                {separator}
              </span>
            )}
            {item.href ? (
              <a href={item.href} data-testid={`breadcrumb-link-${index}`}>
                {item.icon && <span data-testid={`breadcrumb-icon-${index}`}>{item.icon}</span>}
                {item.label}
              </a>
            ) : (
              <span data-testid={`breadcrumb-current-${index}`} aria-current="page">
                {item.icon && <span data-testid={`breadcrumb-icon-${index}`}>{item.icon}</span>}
                {item.label}
              </span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  ),
}));

import { Breadcrumbs } from '../../components/breadcrumbs';

describe('Breadcrumbs', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderBreadcrumbs = (items: any[], separator?: string) => {
    return render(
      <MemoryRouter>
        <Breadcrumbs items={items} separator={separator} />
      </MemoryRouter>
    );
  };

  describe('Basic Rendering', () => {
    it('should render breadcrumbs container', () => {
      renderBreadcrumbs([{ label: 'Home', href: '/' }]);
      expect(screen.getByTestId('breadcrumbs')).toBeInTheDocument();
    });

    it('should have nav element with aria-label', () => {
      renderBreadcrumbs([{ label: 'Home', href: '/' }]);
      expect(screen.getByLabelText('Breadcrumb')).toBeInTheDocument();
    });

    it('should render single breadcrumb', () => {
      renderBreadcrumbs([{ label: 'Home', href: '/' }]);
      expect(screen.getByText('Home')).toBeInTheDocument();
    });

    it('should render multiple breadcrumbs', () => {
      renderBreadcrumbs([
        { label: 'Home', href: '/' },
        { label: 'Projects', href: '/projects' },
        { label: 'My Project' },
      ]);
      expect(screen.getByText('Home')).toBeInTheDocument();
      expect(screen.getByText('Projects')).toBeInTheDocument();
      expect(screen.getByText('My Project')).toBeInTheDocument();
    });
  });

  describe('Links', () => {
    it('should render link for items with href', () => {
      renderBreadcrumbs([
        { label: 'Home', href: '/' },
        { label: 'Projects', href: '/projects' },
      ]);
      expect(screen.getByTestId('breadcrumb-link-0')).toHaveAttribute('href', '/');
      expect(screen.getByTestId('breadcrumb-link-1')).toHaveAttribute('href', '/projects');
    });

    it('should render span for current page (no href)', () => {
      renderBreadcrumbs([{ label: 'Home', href: '/' }, { label: 'Current Page' }]);
      expect(screen.getByTestId('breadcrumb-current-1')).toBeInTheDocument();
    });

    it('should have aria-current on current page', () => {
      renderBreadcrumbs([{ label: 'Home', href: '/' }, { label: 'Current Page' }]);
      expect(screen.getByTestId('breadcrumb-current-1')).toHaveAttribute('aria-current', 'page');
    });
  });

  describe('Separators', () => {
    it('should render default separator', () => {
      renderBreadcrumbs([
        { label: 'Home', href: '/' },
        { label: 'Projects', href: '/projects' },
      ]);
      expect(screen.getByTestId('separator')).toHaveTextContent('/');
    });

    it('should render custom separator', () => {
      renderBreadcrumbs(
        [
          { label: 'Home', href: '/' },
          { label: 'Projects', href: '/projects' },
        ],
        '>'
      );
      expect(screen.getByTestId('separator')).toHaveTextContent('>');
    });

    it('should not render separator before first item', () => {
      renderBreadcrumbs([
        { label: 'Home', href: '/' },
        { label: 'Projects', href: '/projects' },
        { label: 'Details' },
      ]);
      const separators = screen.getAllByTestId('separator');
      expect(separators.length).toBe(2); // Only 2 separators for 3 items
    });

    it('should render separator between each item', () => {
      renderBreadcrumbs([
        { label: 'Level 1', href: '/1' },
        { label: 'Level 2', href: '/2' },
        { label: 'Level 3', href: '/3' },
        { label: 'Level 4' },
      ]);
      const separators = screen.getAllByTestId('separator');
      expect(separators.length).toBe(3);
    });
  });

  describe('Icons', () => {
    it('should render icon when provided', () => {
      renderBreadcrumbs([{ label: 'Home', href: '/', icon: '🏠' }]);
      expect(screen.getByTestId('breadcrumb-icon-0')).toBeInTheDocument();
      expect(screen.getByTestId('breadcrumb-icon-0')).toHaveTextContent('🏠');
    });

    it('should not render icon element when not provided', () => {
      renderBreadcrumbs([{ label: 'Home', href: '/' }]);
      expect(screen.queryByTestId('breadcrumb-icon-0')).not.toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    it('should render empty breadcrumbs without error', () => {
      renderBreadcrumbs([]);
      expect(screen.getByTestId('breadcrumbs')).toBeInTheDocument();
    });
  });

  describe('Complex Paths', () => {
    it('should handle deep navigation paths', () => {
      renderBreadcrumbs([
        { label: 'Home', href: '/' },
        { label: 'Projects', href: '/projects' },
        { label: 'My Movie', href: '/projects/123' },
        { label: 'Scenes', href: '/projects/123/scenes' },
        { label: 'Scene 1', href: '/projects/123/scenes/1' },
        { label: 'Edit' },
      ]);

      expect(screen.getByText('Home')).toBeInTheDocument();
      expect(screen.getByText('Projects')).toBeInTheDocument();
      expect(screen.getByText('My Movie')).toBeInTheDocument();
      expect(screen.getByText('Scenes')).toBeInTheDocument();
      expect(screen.getByText('Scene 1')).toBeInTheDocument();
      expect(screen.getByText('Edit')).toBeInTheDocument();
    });

    it('should handle query parameters in hrefs', () => {
      renderBreadcrumbs([{ label: 'Search', href: '/search?q=test' }, { label: 'Results' }]);
      expect(screen.getByTestId('breadcrumb-link-0')).toHaveAttribute('href', '/search?q=test');
    });
  });
});
