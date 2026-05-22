/**
 * Tests for ShotCard component.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '../test-utils';
import userEvent from '@testing-library/user-event';
import { ShotCard } from '../../components/shot-card';

const mockShotTypes = [
  { value: 'establishing', label: 'Establishing', description: 'Wide establishing shot' },
  { value: 'close_up', label: 'Close-up', description: 'Close-up shot of subject' },
  { value: 'medium', label: 'Medium', description: 'Medium shot' },
];

const mockCameraMovements = [
  { value: 'static', label: 'Static', description: 'No camera movement' },
  { value: 'pan', label: 'Pan', description: 'Horizontal camera rotation' },
  { value: 'tracking', label: 'Tracking', description: 'Camera follows subject' },
];

const mockCharacters = [
  { id: 'char-1', name: 'JOHN' },
  { id: 'char-2', name: 'MARY' },
];

const createMockShot = (overrides = {}) => ({
  id: 'shot-1',
  shotNumber: '1-A',
  sequenceNumber: 1,
  shotType: 'establishing',
  cameraMovement: 'static',
  description: 'Wide shot of the city skyline at dawn',
  dialogue: undefined,
  action: undefined,
  characterIds: [],
  durationSeconds: 3.5,
  compositionNotes: undefined,
  lightingNotes: undefined,
  state: 'planned',
  ...overrides,
});

describe('ShotCard', () => {
  const mockOnUpdate = vi.fn();
  const mockOnDelete = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const defaultProps = {
    shot: createMockShot(),
    characters: mockCharacters,
    shotTypes: mockShotTypes,
    cameraMovements: mockCameraMovements,
    onUpdate: mockOnUpdate,
    onDelete: mockOnDelete,
  };

  describe('Rendering', () => {
    it('renders shot number correctly', () => {
      render(<ShotCard {...defaultProps} />);

      // Shot number badge shows last part after hyphen
      expect(screen.getByText('A')).toBeInTheDocument();
    });

    it('renders shot type and camera movement', () => {
      render(<ShotCard {...defaultProps} />);

      expect(screen.getByText('Establishing')).toBeInTheDocument();
      expect(screen.getByText('Static')).toBeInTheDocument();
    });

    it('renders duration', () => {
      render(<ShotCard {...defaultProps} />);

      expect(screen.getByText('3.5s')).toBeInTheDocument();
    });

    it('renders description truncated', () => {
      render(<ShotCard {...defaultProps} />);

      expect(screen.getByText('Wide shot of the city skyline at dawn')).toBeInTheDocument();
    });

    it('shows character count when characters are assigned', () => {
      const shot = createMockShot({ characterIds: ['char-1', 'char-2'] });
      render(<ShotCard {...defaultProps} shot={shot} />);

      expect(screen.getByText('2')).toBeInTheDocument();
    });

    it('does not show character count when no characters', () => {
      render(<ShotCard {...defaultProps} />);

      // Should not find character count
      const characterCounts = screen.queryAllByText(/^[0-9]+$/);
      // Only duration should be there (3.5s contains numbers but also letters)
      expect(characterCounts.length).toBe(0);
    });
  });

  describe('Expansion', () => {
    it('expands when clicking chevron', async () => {
      const user = userEvent.setup();
      const shot = createMockShot({
        dialogue: 'Hello, world!',
        action: 'Character walks in',
      });
      render(<ShotCard {...defaultProps} shot={shot} />);

      // Initially collapsed - detailed content not visible
      expect(screen.queryByText(/Dialogue/)).not.toBeInTheDocument();

      // Click expand button
      const expandButton = screen
        .getAllByRole('button')
        .find((btn) => btn.querySelector('svg')?.classList.contains('w-4'));
      await user.click(expandButton!);

      // Now expanded
      expect(screen.getByText('Dialogue')).toBeInTheDocument();
      expect(screen.getByText(/"Hello, world!"/)).toBeInTheDocument();
    });

    it('shows dialogue when expanded', async () => {
      const user = userEvent.setup();
      const shot = createMockShot({ dialogue: 'Test dialogue' });
      render(<ShotCard {...defaultProps} shot={shot} />);

      // Expand
      const buttons = screen.getAllByRole('button');
      const expandButton = buttons[buttons.length - 1];
      await user.click(expandButton);

      expect(screen.getByText('"Test dialogue"')).toBeInTheDocument();
    });

    it('shows action when expanded', async () => {
      const user = userEvent.setup();
      const shot = createMockShot({ action: 'Character runs away' });
      render(<ShotCard {...defaultProps} shot={shot} />);

      // Expand
      const buttons = screen.getAllByRole('button');
      const expandButton = buttons[buttons.length - 1];
      await user.click(expandButton);

      expect(screen.getByText('Character runs away')).toBeInTheDocument();
    });

    it('shows characters when expanded', async () => {
      const user = userEvent.setup();
      const shot = createMockShot({ characterIds: ['char-1'] });
      render(<ShotCard {...defaultProps} shot={shot} />);

      // Expand
      const buttons = screen.getAllByRole('button');
      const expandButton = buttons[buttons.length - 1];
      await user.click(expandButton);

      expect(screen.getByText('JOHN')).toBeInTheDocument();
    });
  });

  describe('Editing', () => {
    it('enters edit mode when clicking edit button', async () => {
      const user = userEvent.setup();
      render(<ShotCard {...defaultProps} />);

      // First expand
      const buttons = screen.getAllByRole('button');
      const expandButton = buttons[buttons.length - 1];
      await user.click(expandButton);

      // Click edit button (has Edit2 icon)
      const editButton = screen.getByTitle('Edit shot');
      await user.click(editButton);

      // Should see form elements
      expect(screen.getByLabelText('Shot Type')).toBeInTheDocument();
      expect(screen.getByLabelText('Camera Movement')).toBeInTheDocument();
      expect(screen.getByLabelText('Description')).toBeInTheDocument();
    });

    it('saves changes on save button click', async () => {
      const user = userEvent.setup();
      render(<ShotCard {...defaultProps} />);

      // Expand and edit
      const buttons = screen.getAllByRole('button');
      await user.click(buttons[buttons.length - 1]);
      await user.click(screen.getByTitle('Edit shot'));

      // Change description
      const descriptionInput = screen.getByLabelText('Description');
      await user.clear(descriptionInput);
      await user.type(descriptionInput, 'New description');

      // Save
      await user.click(screen.getByText('Save Changes'));

      expect(mockOnUpdate).toHaveBeenCalledWith(
        'shot-1',
        expect.objectContaining({
          description: 'New description',
        })
      );
    });

    it('cancels changes on cancel button click', async () => {
      const user = userEvent.setup();
      render(<ShotCard {...defaultProps} />);

      // Expand and edit
      const buttons = screen.getAllByRole('button');
      await user.click(buttons[buttons.length - 1]);
      await user.click(screen.getByTitle('Edit shot'));

      // Change something
      const descriptionInput = screen.getByLabelText('Description');
      await user.clear(descriptionInput);
      await user.type(descriptionInput, 'New description');

      // Cancel
      await user.click(screen.getByText('Cancel'));

      expect(mockOnUpdate).not.toHaveBeenCalled();
    });

    it('updates shot type via dropdown', async () => {
      const user = userEvent.setup();
      render(<ShotCard {...defaultProps} />);

      // Expand and edit
      const buttons = screen.getAllByRole('button');
      await user.click(buttons[buttons.length - 1]);
      await user.click(screen.getByTitle('Edit shot'));

      // Change shot type
      const shotTypeSelect = screen.getByLabelText('Shot Type');
      await user.selectOptions(shotTypeSelect, 'close_up');

      // Save
      await user.click(screen.getByText('Save Changes'));

      expect(mockOnUpdate).toHaveBeenCalledWith(
        'shot-1',
        expect.objectContaining({
          shotType: 'close_up',
        })
      );
    });

    it('updates duration via input', async () => {
      const user = userEvent.setup();
      render(<ShotCard {...defaultProps} />);

      // Expand and edit
      const buttons = screen.getAllByRole('button');
      await user.click(buttons[buttons.length - 1]);
      await user.click(screen.getByTitle('Edit shot'));

      // Change duration
      const durationInput = screen.getByLabelText('Duration (seconds)');
      await user.clear(durationInput);
      await user.type(durationInput, '5');

      // Save
      await user.click(screen.getByText('Save Changes'));

      expect(mockOnUpdate).toHaveBeenCalledWith(
        'shot-1',
        expect.objectContaining({
          durationSeconds: 5,
        })
      );
    });
  });

  describe('Deletion', () => {
    it('calls onDelete when delete button clicked', async () => {
      const user = userEvent.setup();
      render(<ShotCard {...defaultProps} />);

      const deleteButton = screen.getByTitle('Delete shot');
      await user.click(deleteButton);

      expect(mockOnDelete).toHaveBeenCalledWith('shot-1');
    });
  });

  describe('Disabled State', () => {
    it('disables edit button when disabled', () => {
      render(<ShotCard {...defaultProps} disabled={true} />);

      expect(screen.getByTitle('Edit shot')).toBeDisabled();
    });

    it('disables delete button when disabled', () => {
      render(<ShotCard {...defaultProps} disabled={true} />);

      expect(screen.getByTitle('Delete shot')).toBeDisabled();
    });

    it('applies disabled styles', () => {
      const { container } = render(<ShotCard {...defaultProps} disabled={true} />);

      const card = container.firstChild as HTMLElement;
      expect(card).toHaveClass('opacity-50');
      expect(card).toHaveClass('pointer-events-none');
    });
  });

  describe('Dragging State', () => {
    it('applies dragging styles when isDragging is true', () => {
      const { container } = render(<ShotCard {...defaultProps} isDragging={true} />);

      const card = container.firstChild as HTMLElement;
      expect(card).toHaveClass('opacity-50');
      expect(card).toHaveClass('scale-95');
    });
  });

  describe('Technical Notes', () => {
    it('shows composition notes when expanded', async () => {
      const user = userEvent.setup();
      const shot = createMockShot({
        compositionNotes: 'Rule of thirds, leading lines',
      });
      render(<ShotCard {...defaultProps} shot={shot} />);

      // Expand
      const buttons = screen.getAllByRole('button');
      await user.click(buttons[buttons.length - 1]);

      expect(screen.getByText('Rule of thirds, leading lines')).toBeInTheDocument();
    });

    it('shows lighting notes when expanded', async () => {
      const user = userEvent.setup();
      const shot = createMockShot({
        lightingNotes: 'Golden hour, warm tones',
      });
      render(<ShotCard {...defaultProps} shot={shot} />);

      // Expand
      const buttons = screen.getAllByRole('button');
      await user.click(buttons[buttons.length - 1]);

      expect(screen.getByText('Golden hour, warm tones')).toBeInTheDocument();
    });

    it('can edit composition and lighting notes', async () => {
      const user = userEvent.setup();
      render(<ShotCard {...defaultProps} />);

      // Expand and edit
      const buttons = screen.getAllByRole('button');
      await user.click(buttons[buttons.length - 1]);
      await user.click(screen.getByTitle('Edit shot'));

      // Fill in notes
      const compositionInput = screen.getByPlaceholderText('Framing, rule of thirds, etc.');
      await user.type(compositionInput, 'Center framing');

      const lightingInput = screen.getByPlaceholderText('Key light, mood, etc.');
      await user.type(lightingInput, 'Low key lighting');

      // Save
      await user.click(screen.getByText('Save Changes'));

      expect(mockOnUpdate).toHaveBeenCalledWith(
        'shot-1',
        expect.objectContaining({
          compositionNotes: 'Center framing',
          lightingNotes: 'Low key lighting',
        })
      );
    });
  });
});
