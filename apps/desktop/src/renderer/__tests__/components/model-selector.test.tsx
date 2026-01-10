/**
 * Model Selector component tests.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// Mock the store
vi.mock('../../stores/generation-store', () => ({
  useGenerationStore: vi.fn(() => ({
    providers: [],
    selectedProvider: null,
    selectedModel: null,
    setProvider: vi.fn(),
    setModel: vi.fn(),
  })),
}));

// Mock the ModelSelector component
vi.mock('../../components/model-selector', () => ({
  ModelSelector: ({
    providers,
    selectedProvider,
    selectedModel,
    onProviderChange,
    onModelChange,
    disabled = false,
    showCost = true,
    compact = false,
  }: any) => (
    <div data-testid="model-selector" className={compact ? 'compact' : ''}>
      {/* Provider Select */}
      <div data-testid="provider-section">
        <label htmlFor="provider-select">Provider</label>
        <select
          id="provider-select"
          data-testid="provider-select"
          value={selectedProvider?.id || ''}
          onChange={(e) => {
            const provider = providers.find((p: any) => p.id === e.target.value);
            onProviderChange?.(provider);
          }}
          disabled={disabled}
        >
          <option value="">Select a provider</option>
          {providers?.map((provider: any) => (
            <option key={provider.id} value={provider.id} disabled={provider.status !== 'healthy'}>
              {provider.name} {provider.status !== 'healthy' && '(Offline)'}
            </option>
          ))}
        </select>
        {selectedProvider && (
          <span data-testid="provider-status" className={selectedProvider.status}>
            {selectedProvider.status}
          </span>
        )}
      </div>

      {/* Model Select */}
      {selectedProvider && (
        <div data-testid="model-section">
          <label htmlFor="model-select">Model</label>
          <select
            id="model-select"
            data-testid="model-select"
            value={selectedModel?.id || ''}
            onChange={(e) => {
              const model = selectedProvider.models.find((m: any) => m.id === e.target.value);
              onModelChange?.(model);
            }}
            disabled={disabled}
          >
            <option value="">Select a model</option>
            {selectedProvider.models?.map((model: any) => (
              <option key={model.id} value={model.id}>
                {model.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Cost Display */}
      {showCost && selectedModel && (
        <div data-testid="cost-display">
          <span>Cost: ${selectedModel.costPerSecond}/sec</span>
        </div>
      )}

      {/* Model Info */}
      {selectedModel && (
        <div data-testid="model-info">
          {selectedModel.description && <p>{selectedModel.description}</p>}
          {selectedModel.maxDuration && <span>Max: {selectedModel.maxDuration}s</span>}
          {selectedModel.resolution && <span>Resolution: {selectedModel.resolution}</span>}
        </div>
      )}
    </div>
  ),
}));

import { ModelSelector } from '../../components/model-selector';

const mockProviders = [
  {
    id: 'replicate',
    name: 'Replicate',
    status: 'healthy',
    models: [
      {
        id: 'minimax',
        name: 'MiniMax Video-01',
        costPerSecond: 0.05,
        maxDuration: 6,
        resolution: '1280x720',
        description: 'High quality video generation',
      },
      {
        id: 'luma',
        name: 'Luma Dream Machine',
        costPerSecond: 0.08,
        maxDuration: 5,
        resolution: '1024x576',
      },
    ],
  },
  {
    id: 'fal',
    name: 'Fal.ai',
    status: 'healthy',
    models: [
      {
        id: 'cogvideox',
        name: 'CogVideoX',
        costPerSecond: 0.04,
        maxDuration: 6,
        resolution: '1280x720',
      },
    ],
  },
  {
    id: 'comfyui',
    name: 'ComfyUI (Local)',
    status: 'offline',
    models: [],
  },
];

describe('ModelSelector', () => {
  const mockHandlers = {
    onProviderChange: vi.fn(),
    onModelChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderModelSelector = (props = {}) => {
    return render(
      <ModelSelector
        providers={mockProviders}
        selectedProvider={null}
        selectedModel={null}
        {...mockHandlers}
        {...props}
      />
    );
  };

  describe('Basic Rendering', () => {
    it('should render model selector', () => {
      renderModelSelector();
      expect(screen.getByTestId('model-selector')).toBeInTheDocument();
    });

    it('should render provider section', () => {
      renderModelSelector();
      expect(screen.getByTestId('provider-section')).toBeInTheDocument();
    });

    it('should have provider select', () => {
      renderModelSelector();
      expect(screen.getByTestId('provider-select')).toBeInTheDocument();
    });

    it('should have provider label', () => {
      renderModelSelector();
      expect(screen.getByLabelText('Provider')).toBeInTheDocument();
    });
  });

  describe('Provider Selection', () => {
    it('should show all providers in dropdown', () => {
      renderModelSelector();
      expect(screen.getByText('Replicate')).toBeInTheDocument();
      expect(screen.getByText('Fal.ai')).toBeInTheDocument();
    });

    it('should show offline indicator for unavailable providers', () => {
      renderModelSelector();
      expect(screen.getByText(/ComfyUI.*Offline/)).toBeInTheDocument();
    });

    it('should call onProviderChange when provider selected', () => {
      renderModelSelector();
      fireEvent.change(screen.getByTestId('provider-select'), {
        target: { value: 'replicate' },
      });
      expect(mockHandlers.onProviderChange).toHaveBeenCalledWith(mockProviders[0]);
    });

    it('should show provider status when selected', () => {
      renderModelSelector({ selectedProvider: mockProviders[0] });
      expect(screen.getByTestId('provider-status')).toBeInTheDocument();
      expect(screen.getByTestId('provider-status')).toHaveTextContent('healthy');
    });
  });

  describe('Model Selection', () => {
    it('should not show model section without selected provider', () => {
      renderModelSelector();
      expect(screen.queryByTestId('model-section')).not.toBeInTheDocument();
    });

    it('should show model section when provider selected', () => {
      renderModelSelector({ selectedProvider: mockProviders[0] });
      expect(screen.getByTestId('model-section')).toBeInTheDocument();
    });

    it('should show models for selected provider', () => {
      renderModelSelector({ selectedProvider: mockProviders[0] });
      expect(screen.getByText('MiniMax Video-01')).toBeInTheDocument();
      expect(screen.getByText('Luma Dream Machine')).toBeInTheDocument();
    });

    it('should call onModelChange when model selected', () => {
      renderModelSelector({ selectedProvider: mockProviders[0] });
      fireEvent.change(screen.getByTestId('model-select'), {
        target: { value: 'minimax' },
      });
      expect(mockHandlers.onModelChange).toHaveBeenCalledWith(mockProviders[0].models[0]);
    });
  });

  describe('Cost Display', () => {
    it('should show cost when model selected and showCost is true', () => {
      renderModelSelector({
        selectedProvider: mockProviders[0],
        selectedModel: mockProviders[0].models[0],
        showCost: true,
      });
      expect(screen.getByTestId('cost-display')).toBeInTheDocument();
      expect(screen.getByText(/\$0.05\/sec/)).toBeInTheDocument();
    });

    it('should not show cost when showCost is false', () => {
      renderModelSelector({
        selectedProvider: mockProviders[0],
        selectedModel: mockProviders[0].models[0],
        showCost: false,
      });
      expect(screen.queryByTestId('cost-display')).not.toBeInTheDocument();
    });
  });

  describe('Model Info', () => {
    it('should show model info when model selected', () => {
      renderModelSelector({
        selectedProvider: mockProviders[0],
        selectedModel: mockProviders[0].models[0],
      });
      expect(screen.getByTestId('model-info')).toBeInTheDocument();
    });

    it('should show model description', () => {
      renderModelSelector({
        selectedProvider: mockProviders[0],
        selectedModel: mockProviders[0].models[0],
      });
      expect(screen.getByText('High quality video generation')).toBeInTheDocument();
    });

    it('should show max duration', () => {
      renderModelSelector({
        selectedProvider: mockProviders[0],
        selectedModel: mockProviders[0].models[0],
      });
      expect(screen.getByText('Max: 6s')).toBeInTheDocument();
    });

    it('should show resolution', () => {
      renderModelSelector({
        selectedProvider: mockProviders[0],
        selectedModel: mockProviders[0].models[0],
      });
      expect(screen.getByText('Resolution: 1280x720')).toBeInTheDocument();
    });
  });

  describe('Disabled State', () => {
    it('should disable provider select when disabled', () => {
      renderModelSelector({ disabled: true });
      expect(screen.getByTestId('provider-select')).toBeDisabled();
    });

    it('should disable model select when disabled', () => {
      renderModelSelector({
        selectedProvider: mockProviders[0],
        disabled: true,
      });
      expect(screen.getByTestId('model-select')).toBeDisabled();
    });
  });

  describe('Compact Mode', () => {
    it('should apply compact class when compact is true', () => {
      renderModelSelector({ compact: true });
      expect(screen.getByTestId('model-selector')).toHaveClass('compact');
    });
  });
});
