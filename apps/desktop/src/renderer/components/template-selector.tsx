/**
 * Template selector component for new project creation.
 * Displays available project templates with preview and selection.
 */

import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Film,
  Clock,
  Zap,
  Palette,
  Camera,
  Search,
  Check,
  Loader2,
  Layout,
  Star,
  Tag,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useTranslation } from '../i18n/use-translation';

// Template interface
export interface ProjectTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  thumbnail?: string;
  defaultResolution: string;
  defaultFps: number;
  defaultShotDuration: number;
  visualStyle: string;
  colorPalette: string[];
  lightingStyle: string;
  pacing: string;
  avgShotsPerScene: number;
  tags: string[];
}

interface TemplateSelectorProps {
  selectedTemplate: string | null;
  onSelectTemplate: (templateId: string | null) => void;
  onApplySettings?: (settings: Record<string, any>) => void;
}

// Category badges
const categoryColors: Record<string, string> = {
  film: 'bg-purple-500/20 text-purple-400',
  short: 'bg-blue-500/20 text-blue-400',
  commercial: 'bg-green-500/20 text-green-400',
  music_video: 'bg-pink-500/20 text-pink-400',
  documentary: 'bg-yellow-500/20 text-yellow-400',
  experimental: 'bg-orange-500/20 text-orange-400',
};

// Pacing indicator
function PacingIndicator({ pacing }: { pacing: string }) {
  const bars = pacing === 'fast' ? 3 : pacing === 'moderate' ? 2 : 1;

  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className={cn('w-1 h-3 rounded-full', i <= bars ? 'bg-brand-400' : 'bg-surface-700')}
        />
      ))}
    </div>
  );
}

// Color palette preview
function ColorPalettePreview({ colors }: { colors: string[] }) {
  return (
    <div className="flex gap-0.5">
      {colors.slice(0, 5).map((color, i) => (
        <div
          key={i}
          className="w-4 h-4 rounded-sm first:rounded-l last:rounded-r"
          style={{ backgroundColor: color }}
        />
      ))}
    </div>
  );
}

// Template card
function TemplateCard({
  template,
  isSelected,
  onSelect,
}: {
  template: ProjectTemplate;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const { t } = useTranslation();
  return (
    <button
      onClick={onSelect}
      className={cn(
        'relative p-4 rounded-lg border text-left transition-all',
        isSelected
          ? 'border-brand-500 bg-brand-500/10 ring-2 ring-brand-500/50'
          : 'border-surface-700 bg-surface-800/50 hover:border-surface-600 hover:bg-surface-800'
      )}
    >
      {/* Selection indicator */}
      {isSelected && (
        <div className="absolute top-2 right-2 w-6 h-6 rounded-full bg-brand-500 flex items-center justify-center">
          <Check className="w-4 h-4 text-white" />
        </div>
      )}

      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div>
          <h3 className="font-medium">{template.name}</h3>
          <span
            className={cn(
              'inline-block px-2 py-0.5 text-xs rounded mt-1',
              categoryColors[template.category] || 'bg-surface-700 text-surface-400'
            )}
          >
            {template.category.replace('_', ' ')}
          </span>
        </div>
      </div>

      {/* Description */}
      <p className="text-sm text-surface-400 mb-3 line-clamp-2">{template.description}</p>

      {/* Color palette */}
      <div className="mb-3">
        <ColorPalettePreview colors={template.colorPalette} />
      </div>

      {/* Stats row */}
      <div className="flex items-center gap-4 text-xs text-surface-400">
        <div className="flex items-center gap-1">
          <Clock className="w-3 h-3" />
          {template.defaultShotDuration}s
        </div>
        <div className="flex items-center gap-1">
          <Camera className="w-3 h-3" />
          {template.defaultFps} fps
        </div>
        <div
          className="flex items-center gap-1"
          title={`${t('templateSel.pacingLabel', 'Pacing')}: ${template.pacing}`}
        >
          <Zap className="w-3 h-3" />
          <PacingIndicator pacing={template.pacing} />
        </div>
      </div>

      {/* Tags */}
      {template.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-3">
          {template.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="px-1.5 py-0.5 bg-surface-700 text-surface-400 text-xs rounded"
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </button>
  );
}

export function TemplateSelector({
  selectedTemplate,
  onSelectTemplate,
  onApplySettings,
}: TemplateSelectorProps) {
  const { t } = useTranslation();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  // Fetch templates
  const { data: templates, isLoading } = useQuery({
    queryKey: ['templates', selectedCategory],
    queryFn: async () => {
      return window.electronAPI.backendRequest<ProjectTemplate[]>('templates.list', {
        category: selectedCategory,
      });
    },
  });

  // Fetch categories
  const { data: categories } = useQuery({
    queryKey: ['template-categories'],
    queryFn: async () => {
      return window.electronAPI.backendRequest<Array<{ id: string; name: string; count: number }>>(
        'templates.getCategories',
        {}
      );
    },
  });

  // Fetch featured templates
  const { data: featuredTemplates } = useQuery({
    queryKey: ['featured-templates'],
    queryFn: async () => {
      return window.electronAPI.backendRequest<ProjectTemplate[]>('templates.getFeatured', {
        limit: 4,
      });
    },
  });

  // Filter templates by search
  const filteredTemplates = templates?.filter((t) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      t.name.toLowerCase().includes(q) ||
      t.description.toLowerCase().includes(q) ||
      t.tags.some((tag) => tag.toLowerCase().includes(q))
    );
  });

  // Handle template selection
  const handleSelect = async (templateId: string | null) => {
    onSelectTemplate(templateId);

    // Fetch and apply template settings if callback provided
    if (templateId && onApplySettings) {
      try {
        const settings = await window.electronAPI.backendRequest<Record<string, any>>(
          'templates.getSettings',
          { template_id: templateId }
        );
        if (settings) {
          onApplySettings(settings);
        }
      } catch (err) {
        console.error('Failed to fetch template settings:', err);
      }
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-lg font-medium flex items-center gap-2">
          <Layout className="w-5 h-5 text-brand-400" />
          {t('templateSel.projectTemplate', 'Project Template')}
        </h2>
        <p className="text-sm text-surface-400 mt-1">
          {t(
            'templateSel.projectTemplateDesc',
            'Choose a template to set up default visual styles and generation settings'
          )}
        </p>
      </div>

      {/* Search and filters */}
      <div className="flex gap-4">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t('templateSel.searchPlaceholder', 'Search templates...')}
            className="w-full pl-10 pr-4 py-2 bg-surface-800 border border-surface-700 rounded-lg"
          />
        </div>

        {/* Category filter */}
        <select
          value={selectedCategory || ''}
          onChange={(e) => setSelectedCategory(e.target.value || null)}
          className="px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg"
        >
          <option value="">{t('templateSel.allCategories', 'All Categories')}</option>
          {categories?.map((cat) => (
            <option key={cat.id} value={cat.id}>
              {cat.name} ({cat.count})
            </option>
          ))}
        </select>
      </div>

      {/* Skip template option */}
      <button
        onClick={() => handleSelect(null)}
        className={cn(
          'w-full p-4 rounded-lg border text-left transition-all flex items-center gap-4',
          !selectedTemplate
            ? 'border-brand-500 bg-brand-500/10'
            : 'border-surface-700 bg-surface-800/50 hover:border-surface-600'
        )}
      >
        <div className="w-12 h-12 rounded-lg bg-surface-700 flex items-center justify-center">
          <Film className="w-6 h-6 text-surface-400" />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className="font-medium">{t('templateSel.blankProject', 'Blank Project')}</h3>
            {!selectedTemplate && (
              <div className="w-5 h-5 rounded-full bg-brand-500 flex items-center justify-center">
                <Check className="w-3 h-3 text-white" />
              </div>
            )}
          </div>
          <p className="text-sm text-surface-400">
            {t('templateSel.blankProjectDesc', 'Start from scratch with default settings')}
          </p>
        </div>
      </button>

      {/* Featured templates */}
      {!searchQuery && !selectedCategory && featuredTemplates && featuredTemplates.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-surface-400 flex items-center gap-2 mb-3">
            <Star className="w-4 h-4" />
            {t('templateSel.featuredTemplates', 'Featured Templates')}
          </h3>
          <div className="grid grid-cols-2 gap-3">
            {featuredTemplates.map((template) => (
              <TemplateCard
                key={template.id}
                template={template}
                isSelected={selectedTemplate === template.id}
                onSelect={() => handleSelect(template.id)}
              />
            ))}
          </div>
        </div>
      )}

      {/* All templates */}
      <div>
        <h3 className="text-sm font-medium text-surface-400 flex items-center gap-2 mb-3">
          <Tag className="w-4 h-4" />
          {searchQuery
            ? t('templateSel.searchResults', 'Search Results')
            : selectedCategory
              ? t('templateSel.filteredTemplates', 'Filtered Templates')
              : t('templateSel.allTemplates', 'All Templates')}
        </h3>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-brand-400" />
          </div>
        ) : filteredTemplates && filteredTemplates.length > 0 ? (
          <div className="grid grid-cols-2 gap-3 max-h-80 overflow-y-auto pr-2">
            {filteredTemplates.map((template) => (
              <TemplateCard
                key={template.id}
                template={template}
                isSelected={selectedTemplate === template.id}
                onSelect={() => handleSelect(template.id)}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-surface-400">
            <Layout className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>{t('templateSel.noTemplatesFound', 'No templates found')}</p>
          </div>
        )}
      </div>

      {/* Selected template details */}
      {selectedTemplate && templates && (
        <SelectedTemplateDetails template={templates.find((t) => t.id === selectedTemplate)} />
      )}
    </div>
  );
}

// Selected template details panel
function SelectedTemplateDetails({ template }: { template?: ProjectTemplate }) {
  const { t } = useTranslation();
  if (!template) return null;

  return (
    <div className="p-4 bg-surface-800/50 rounded-lg border border-brand-500/30">
      <h4 className="font-medium mb-3 flex items-center gap-2">
        <Check className="w-4 h-4 text-brand-400" />
        {t('templateSel.selected', 'Selected')}: {template.name}
      </h4>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
        <div>
          <span className="text-surface-400">{t('templateSel.resolution', 'Resolution')}</span>
          <p className="font-medium">{template.defaultResolution}</p>
        </div>
        <div>
          <span className="text-surface-400">{t('templateSel.frameRate', 'Frame Rate')}</span>
          <p className="font-medium">{template.defaultFps} fps</p>
        </div>
        <div>
          <span className="text-surface-400">{t('templateSel.shotDuration', 'Shot Duration')}</span>
          <p className="font-medium">{template.defaultShotDuration}s</p>
        </div>
        <div>
          <span className="text-surface-400">{t('templateSel.pacingLabel', 'Pacing')}</span>
          <p className="font-medium capitalize">{template.pacing}</p>
        </div>
        <div>
          <span className="text-surface-400">{t('templateSel.visualStyle', 'Visual Style')}</span>
          <p className="font-medium capitalize">{template.visualStyle.replace('_', ' ')}</p>
        </div>
        <div>
          <span className="text-surface-400">{t('templateSel.lighting', 'Lighting')}</span>
          <p className="font-medium capitalize">{template.lightingStyle.replace('_', ' ')}</p>
        </div>
        <div>
          <span className="text-surface-400">{t('templateSel.shotsPerScene', 'Shots/Scene')}</span>
          <p className="font-medium">~{template.avgShotsPerScene}</p>
        </div>
        <div>
          <span className="text-surface-400">{t('templateSel.colorPalette', 'Color Palette')}</span>
          <ColorPalettePreview colors={template.colorPalette} />
        </div>
      </div>
    </div>
  );
}

export default TemplateSelector;
