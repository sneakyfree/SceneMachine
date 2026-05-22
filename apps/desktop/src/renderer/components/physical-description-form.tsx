/**
 * Physical Description Form component.
 *
 * A comprehensive form for editing character physical appearance details.
 * Aligns with the backend PhysicalDescription schema.
 */

import { useState, useCallback } from 'react';
import {
  User,
  Palette,
  Ruler,
  Eye,
  Scissors,
  Shirt,
  Sparkles,
  X,
  Plus,
  Save,
  RotateCcw,
} from 'lucide-react';
import { cn } from '../lib/utils';

export interface PhysicalDescription {
  hair_color: string;
  hair_style: string;
  eye_color: string;
  skin_tone: string;
  height: string;
  build: string;
  distinguishing_features: string[];
  clothing_style: string;
  additional_notes: string;
}

interface PhysicalDescriptionFormProps {
  initialData?: Partial<PhysicalDescription>;
  onSave: (data: PhysicalDescription) => void;
  onCancel?: () => void;
  isLocked?: boolean;
  isLoading?: boolean;
  compact?: boolean;
}

// Preset options for dropdowns
const HAIR_COLORS = [
  'Black',
  'Brown',
  'Blonde',
  'Auburn',
  'Red',
  'Gray',
  'White',
  'Silver',
  'Platinum',
  'Strawberry Blonde',
  'Chestnut',
  'Salt and Pepper',
];

const HAIR_STYLES = [
  'Short',
  'Medium',
  'Long',
  'Curly',
  'Wavy',
  'Straight',
  'Bald',
  'Shaved',
  'Braided',
  'Ponytail',
  'Bun',
  'Afro',
  'Dreadlocks',
  'Pixie Cut',
  'Buzz Cut',
];

const EYE_COLORS = ['Brown', 'Blue', 'Green', 'Hazel', 'Gray', 'Amber', 'Black'];

const SKIN_TONES = ['Fair', 'Light', 'Medium', 'Olive', 'Tan', 'Brown', 'Dark Brown', 'Dark'];

const HEIGHT_OPTIONS = [
  'Very Short',
  'Short',
  'Below Average',
  'Average',
  'Above Average',
  'Tall',
  'Very Tall',
];

const BUILD_OPTIONS = [
  'Slim',
  'Lean',
  'Average',
  'Athletic',
  'Muscular',
  'Stocky',
  'Heavy',
  'Plus-size',
];

const emptyDescription: PhysicalDescription = {
  hair_color: '',
  hair_style: '',
  eye_color: '',
  skin_tone: '',
  height: '',
  build: '',
  distinguishing_features: [],
  clothing_style: '',
  additional_notes: '',
};

export function PhysicalDescriptionForm({
  initialData,
  onSave,
  onCancel,
  isLocked = false,
  isLoading = false,
  compact = false,
}: PhysicalDescriptionFormProps) {
  const [formData, setFormData] = useState<PhysicalDescription>({
    ...emptyDescription,
    ...initialData,
    distinguishing_features: initialData?.distinguishing_features ?? [],
  });

  const [newFeature, setNewFeature] = useState('');
  const [hasChanges, setHasChanges] = useState(false);

  const updateField = useCallback(
    <K extends keyof PhysicalDescription>(field: K, value: PhysicalDescription[K]) => {
      setFormData((prev) => ({ ...prev, [field]: value }));
      setHasChanges(true);
    },
    []
  );

  const addFeature = useCallback(() => {
    if (newFeature.trim() && !formData.distinguishing_features.includes(newFeature.trim())) {
      updateField('distinguishing_features', [
        ...formData.distinguishing_features,
        newFeature.trim(),
      ]);
      setNewFeature('');
    }
  }, [newFeature, formData.distinguishing_features, updateField]);

  const removeFeature = useCallback(
    (feature: string) => {
      updateField(
        'distinguishing_features',
        formData.distinguishing_features.filter((f) => f !== feature)
      );
    },
    [formData.distinguishing_features, updateField]
  );

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      onSave(formData);
      setHasChanges(false);
    },
    [formData, onSave]
  );

  const handleReset = useCallback(() => {
    setFormData({
      ...emptyDescription,
      ...initialData,
      distinguishing_features: initialData?.distinguishing_features ?? [],
    });
    setHasChanges(false);
  }, [initialData]);

  const SelectField = ({
    label,
    icon: Icon,
    field,
    options,
    allowCustom = true,
  }: {
    label: string;
    icon: typeof User;
    field: keyof PhysicalDescription;
    options: string[];
    allowCustom?: boolean;
  }) => (
    <div className={cn('space-y-1.5', compact && 'space-y-1')}>
      <label className="flex items-center gap-1.5 text-sm font-medium text-surface-400">
        <Icon className="w-3.5 h-3.5" />
        {label}
      </label>
      <div className="flex gap-2">
        <select
          value={
            options.map((o) => o.toLowerCase()).includes((formData[field] as string).toLowerCase())
              ? (formData[field] as string)
              : ''
          }
          onChange={(e) => updateField(field, e.target.value as any)}
          disabled={isLocked || isLoading}
          className={cn(
            'flex-1 px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg',
            'text-sm focus:outline-none focus:border-brand-500',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            compact && 'py-1.5 text-xs'
          )}
        >
          <option value="">Select {label.toLowerCase()}...</option>
          {options.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
        {allowCustom && (
          <input
            type="text"
            placeholder="Custom..."
            value={
              options
                .map((o) => o.toLowerCase())
                .includes((formData[field] as string).toLowerCase())
                ? ''
                : (formData[field] as string)
            }
            onChange={(e) => updateField(field, e.target.value as any)}
            disabled={isLocked || isLoading}
            className={cn(
              'w-28 px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg',
              'text-sm focus:outline-none focus:border-brand-500 placeholder:text-surface-600',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              compact && 'py-1.5 text-xs w-24'
            )}
          />
        )}
      </div>
    </div>
  );

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Hair Section */}
      <div className="grid grid-cols-2 gap-4">
        <SelectField label="Hair Color" icon={Palette} field="hair_color" options={HAIR_COLORS} />
        <SelectField label="Hair Style" icon={Scissors} field="hair_style" options={HAIR_STYLES} />
      </div>

      {/* Eyes & Skin */}
      <div className="grid grid-cols-2 gap-4">
        <SelectField label="Eye Color" icon={Eye} field="eye_color" options={EYE_COLORS} />
        <SelectField label="Skin Tone" icon={Palette} field="skin_tone" options={SKIN_TONES} />
      </div>

      {/* Height & Build */}
      <div className="grid grid-cols-2 gap-4">
        <SelectField
          label="Height"
          icon={Ruler}
          field="height"
          options={HEIGHT_OPTIONS}
          allowCustom={false}
        />
        <SelectField label="Build" icon={User} field="build" options={BUILD_OPTIONS} />
      </div>

      {/* Clothing Style */}
      <div className="space-y-1.5">
        <label className="flex items-center gap-1.5 text-sm font-medium text-surface-400">
          <Shirt className="w-3.5 h-3.5" />
          Clothing Style
        </label>
        <input
          type="text"
          value={formData.clothing_style}
          onChange={(e) => updateField('clothing_style', e.target.value)}
          placeholder="e.g., Business casual, streetwear, formal suits..."
          disabled={isLocked || isLoading}
          className={cn(
            'w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg',
            'text-sm focus:outline-none focus:border-brand-500 placeholder:text-surface-600',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            compact && 'py-1.5 text-xs'
          )}
        />
      </div>

      {/* Distinguishing Features */}
      <div className="space-y-1.5">
        <label className="flex items-center gap-1.5 text-sm font-medium text-surface-400">
          <Sparkles className="w-3.5 h-3.5" />
          Distinguishing Features
        </label>
        <div className="flex flex-wrap gap-2 mb-2">
          {formData.distinguishing_features.map((feature) => (
            <span
              key={feature}
              className={cn(
                'inline-flex items-center gap-1 px-2 py-1 bg-surface-800 rounded-full',
                'text-xs text-surface-200 border border-surface-700'
              )}
            >
              {feature}
              {!isLocked && (
                <button
                  type="button"
                  onClick={() => removeFeature(feature)}
                  className="p-0.5 hover:bg-surface-700 rounded-full transition-colors"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </span>
          ))}
          {formData.distinguishing_features.length === 0 && (
            <span className="text-xs text-surface-500 italic">
              No distinguishing features added
            </span>
          )}
        </div>
        {!isLocked && (
          <div className="flex gap-2">
            <input
              type="text"
              value={newFeature}
              onChange={(e) => setNewFeature(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  addFeature();
                }
              }}
              placeholder="e.g., Scar on left cheek, birthmark, tattoo..."
              disabled={isLoading}
              className={cn(
                'flex-1 px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg',
                'text-sm focus:outline-none focus:border-brand-500 placeholder:text-surface-600',
                compact && 'py-1.5 text-xs'
              )}
            />
            <button
              type="button"
              onClick={addFeature}
              disabled={!newFeature.trim() || isLoading}
              className={cn(
                'px-3 py-2 bg-surface-700 hover:bg-surface-600 rounded-lg transition-colors',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                compact && 'px-2 py-1.5'
              )}
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Additional Notes */}
      {!compact && (
        <div className="space-y-1.5">
          <label className="flex items-center gap-1.5 text-sm font-medium text-surface-400">
            Additional Notes
          </label>
          <textarea
            value={formData.additional_notes}
            onChange={(e) => updateField('additional_notes', e.target.value)}
            placeholder="Any other physical characteristics or notes..."
            disabled={isLocked || isLoading}
            rows={2}
            className={cn(
              'w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg',
              'text-sm focus:outline-none focus:border-brand-500 placeholder:text-surface-600',
              'disabled:opacity-50 disabled:cursor-not-allowed resize-none'
            )}
          />
        </div>
      )}

      {/* Actions */}
      {!isLocked && (
        <div className="flex items-center justify-end gap-2 pt-2 border-t border-surface-800">
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              disabled={isLoading}
              className={cn(
                'px-3 py-2 text-sm text-surface-400 hover:text-surface-200 transition-colors',
                'disabled:opacity-50',
                compact && 'px-2 py-1.5 text-xs'
              )}
            >
              Cancel
            </button>
          )}
          <button
            type="button"
            onClick={handleReset}
            disabled={isLoading || !hasChanges}
            className={cn(
              'flex items-center gap-1.5 px-3 py-2 text-sm text-surface-400',
              'hover:text-surface-200 transition-colors disabled:opacity-50',
              compact && 'px-2 py-1.5 text-xs'
            )}
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Reset
          </button>
          <button
            type="submit"
            disabled={isLoading || !hasChanges}
            className={cn(
              'flex items-center gap-1.5 px-4 py-2 bg-brand-600 hover:bg-brand-500',
              'text-sm font-medium rounded-lg transition-colors',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              compact && 'px-3 py-1.5 text-xs'
            )}
          >
            <Save className="w-3.5 h-3.5" />
            {isLoading ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      )}

      {/* Locked Message */}
      {isLocked && (
        <div className="flex items-center gap-2 px-3 py-2 bg-green-500/10 border border-green-500/30 rounded-lg text-sm text-green-400">
          <span>This character is locked. Unlock to edit physical description.</span>
        </div>
      )}
    </form>
  );
}

/**
 * Read-only summary view of physical description.
 * Used when showing collapsed character info.
 */
export function PhysicalDescriptionSummary({ data }: { data?: Partial<PhysicalDescription> }) {
  if (!data) return null;

  const parts: string[] = [];

  if (data.height) parts.push(data.height);
  if (data.build) parts.push(data.build);
  if (data.hair_color && data.hair_style) {
    parts.push(`${data.hair_color} ${data.hair_style} hair`);
  } else if (data.hair_color) {
    parts.push(`${data.hair_color} hair`);
  }
  if (data.eye_color) parts.push(`${data.eye_color} eyes`);
  if (data.skin_tone) parts.push(`${data.skin_tone} skin`);

  if (parts.length === 0) return null;

  return <p className="text-sm text-surface-300">{parts.join(' • ')}</p>;
}
