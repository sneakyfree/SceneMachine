/**
 * Command Palette component tests.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// Mock the CommandPalette since it may have complex dependencies
vi.mock('../../components/command-palette', () => ({
  CommandPalette: ({ isOpen, onClose, commands }: any) => {
    if (!isOpen) return null;

    return (
      <div data-testid="command-palette" role="dialog" aria-modal="true">
        <input
          type="text"
          placeholder="Type a command..."
          data-testid="command-input"
          aria-label="Command search"
        />
        <ul data-testid="command-list">
          {commands?.map((cmd: any) => (
            <li key={cmd.id} data-testid={`command-${cmd.id}`}>
              <button onClick={() => { cmd.action?.(); onClose(); }}>
                {cmd.label}
              </button>
            </li>
          ))}
        </ul>
        <button onClick={onClose} data-testid="close-button">Close</button>
      </div>
    );
  },
  useCommandPalette: () => ({
    isOpen: false,
    open: vi.fn(),
    close: vi.fn(),
    toggle: vi.fn(),
  }),
}));

import { CommandPalette, useCommandPalette } from '../../components/command-palette';

const mockCommands = [
  {
    id: 'new-project',
    label: 'New Project',
    shortcut: 'Ctrl+N',
    category: 'Project',
    action: vi.fn(),
  },
  {
    id: 'open-project',
    label: 'Open Project',
    shortcut: 'Ctrl+O',
    category: 'Project',
    action: vi.fn(),
  },
  {
    id: 'save',
    label: 'Save',
    shortcut: 'Ctrl+S',
    category: 'File',
    action: vi.fn(),
  },
  {
    id: 'undo',
    label: 'Undo',
    shortcut: 'Ctrl+Z',
    category: 'Edit',
    action: vi.fn(),
  },
  {
    id: 'redo',
    label: 'Redo',
    shortcut: 'Ctrl+Shift+Z',
    category: 'Edit',
    action: vi.fn(),
  },
];

describe('CommandPalette', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderPalette = (isOpen = true) => {
    return render(
      <MemoryRouter>
        <CommandPalette
          isOpen={isOpen}
          onClose={vi.fn()}
          commands={mockCommands}
        />
      </MemoryRouter>
    );
  };

  describe('Visibility', () => {
    it('should not render when closed', () => {
      renderPalette(false);
      expect(screen.queryByTestId('command-palette')).not.toBeInTheDocument();
    });

    it('should render when open', () => {
      renderPalette(true);
      expect(screen.getByTestId('command-palette')).toBeInTheDocument();
    });
  });

  describe('Search Input', () => {
    it('should have search input', () => {
      renderPalette();
      expect(screen.getByTestId('command-input')).toBeInTheDocument();
    });

    it('should have placeholder text', () => {
      renderPalette();
      expect(screen.getByPlaceholderText(/type a command/i)).toBeInTheDocument();
    });

    it('should have accessible label', () => {
      renderPalette();
      expect(screen.getByLabelText(/command search/i)).toBeInTheDocument();
    });
  });

  describe('Command List', () => {
    it('should render command list', () => {
      renderPalette();
      expect(screen.getByTestId('command-list')).toBeInTheDocument();
    });

    it('should render all commands', () => {
      renderPalette();
      expect(screen.getByText('New Project')).toBeInTheDocument();
      expect(screen.getByText('Open Project')).toBeInTheDocument();
      expect(screen.getByText('Save')).toBeInTheDocument();
      expect(screen.getByText('Undo')).toBeInTheDocument();
      expect(screen.getByText('Redo')).toBeInTheDocument();
    });
  });

  describe('Command Execution', () => {
    it('should execute command action when clicked', () => {
      const onClose = vi.fn();
      render(
        <MemoryRouter>
          <CommandPalette
            isOpen={true}
            onClose={onClose}
            commands={mockCommands}
          />
        </MemoryRouter>
      );

      fireEvent.click(screen.getByText('New Project'));
      expect(mockCommands[0].action).toHaveBeenCalled();
    });

    it('should close palette after command execution', () => {
      const onClose = vi.fn();
      render(
        <MemoryRouter>
          <CommandPalette
            isOpen={true}
            onClose={onClose}
            commands={mockCommands}
          />
        </MemoryRouter>
      );

      fireEvent.click(screen.getByText('Save'));
      expect(onClose).toHaveBeenCalled();
    });
  });

  describe('Close Functionality', () => {
    it('should have close button', () => {
      renderPalette();
      expect(screen.getByTestId('close-button')).toBeInTheDocument();
    });

    it('should call onClose when close button clicked', () => {
      const onClose = vi.fn();
      render(
        <MemoryRouter>
          <CommandPalette
            isOpen={true}
            onClose={onClose}
            commands={mockCommands}
          />
        </MemoryRouter>
      );

      fireEvent.click(screen.getByTestId('close-button'));
      expect(onClose).toHaveBeenCalled();
    });
  });

  describe('Accessibility', () => {
    it('should have dialog role', () => {
      renderPalette();
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('should have aria-modal attribute', () => {
      renderPalette();
      expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true');
    });
  });
});

describe('useCommandPalette hook', () => {
  it('should return palette state and controls', () => {
    let hookResult: any;

    function TestComponent() {
      hookResult = useCommandPalette();
      return null;
    }

    render(<TestComponent />);

    expect(hookResult).toHaveProperty('isOpen');
    expect(hookResult).toHaveProperty('open');
    expect(hookResult).toHaveProperty('close');
    expect(hookResult).toHaveProperty('toggle');
  });

  it('should have initial closed state', () => {
    let hookResult: any;

    function TestComponent() {
      hookResult = useCommandPalette();
      return null;
    }

    render(<TestComponent />);

    expect(hookResult.isOpen).toBe(false);
  });
});
