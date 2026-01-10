/**
 * Character Card component tests.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CharacterCard } from '../../components/character-card';

// Mock dependencies
vi.mock('../../stores/experience-store', () => ({
  useExperienceStore: () => ({
    getTerm: (key: string) => {
      const terms: Record<string, string> = {
        locked: 'Locked',
        unlocked: 'Unlocked',
        lock: 'Save Look',
        unlock: 'Edit Look',
      };
      return terms[key] || key;
    },
  }),
}));

vi.mock('../../components/voice-selector', () => ({
  VoiceSelector: () => <div data-testid="voice-selector">Voice Selector</div>,
}));

vi.mock('../../components/physical-description-form', () => ({
  PhysicalDescriptionForm: ({ onSave, onCancel }: any) => (
    <div data-testid="physical-form">
      <button onClick={() => onSave({ hair_color: 'brown' })}>Save</button>
      <button onClick={onCancel}>Cancel</button>
    </div>
  ),
}));

const mockCharacter = {
  id: 'char-1',
  name: 'JOHN',
  screenplayName: 'JOHN',
  description: 'A detective with a mysterious past',
  ageRangeDisplay: '40-50',
  gender: 'male',
  physicalDescription: {
    hair_color: 'brown',
    hair_style: 'short',
    eye_color: 'blue',
    build: 'athletic',
    height: "6'0\"",
    skin_tone: 'fair',
  },
  personalityTraits: ['determined', 'cautious', 'intelligent', 'resourceful', 'stubborn'],
  lockState: 'draft',
  isLocked: false,
  sceneCount: 15,
  dialogueCount: 42,
  isProtagonist: true,
  referenceAssets: [],
  referenceCount: 0,
  voiceId: null,
  voiceProvider: null,
  voiceName: null,
};

const mockHandlers = {
  onEdit: vi.fn(),
  onLock: vi.fn(),
  onUnlock: vi.fn(),
  onUploadReference: vi.fn(),
  onDeleteReference: vi.fn(),
  onGenerateDescription: vi.fn(),
  onUpdatePhysicalDescription: vi.fn(),
  onVoiceChange: vi.fn(),
};

describe('CharacterCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    it('should render character name', () => {
      render(<CharacterCard character={mockCharacter} {...mockHandlers} />);
      expect(screen.getByText('JOHN')).toBeInTheDocument();
    });

    it('should render character avatar with first letter', () => {
      render(<CharacterCard character={mockCharacter} {...mockHandlers} />);
      const avatar = screen.getByText('J');
      expect(avatar).toBeInTheDocument();
    });

    it('should display scene and dialogue counts', () => {
      render(<CharacterCard character={mockCharacter} {...mockHandlers} />);
      expect(screen.getByText('15 scenes')).toBeInTheDocument();
      expect(screen.getByText('42 lines')).toBeInTheDocument();
    });

    it('should display description', () => {
      render(<CharacterCard character={mockCharacter} {...mockHandlers} />);
      expect(screen.getByText('A detective with a mysterious past')).toBeInTheDocument();
    });

    it('should display personality traits', () => {
      render(<CharacterCard character={mockCharacter} {...mockHandlers} />);
      expect(screen.getByText('determined')).toBeInTheDocument();
      expect(screen.getByText('cautious')).toBeInTheDocument();
    });

    it('should show +N more for excess traits', () => {
      render(<CharacterCard character={mockCharacter} {...mockHandlers} />);
      expect(screen.getByText('+1 more')).toBeInTheDocument();
    });
  });

  describe('Lock State', () => {
    it('should show Draft badge for draft state', () => {
      render(<CharacterCard character={mockCharacter} {...mockHandlers} />);
      expect(screen.getByText('Draft')).toBeInTheDocument();
    });

    it('should show Locked badge for locked character', () => {
      const lockedChar = { ...mockCharacter, lockState: 'locked', isLocked: true };
      render(<CharacterCard character={lockedChar} {...mockHandlers} />);
      expect(screen.getByText('Locked')).toBeInTheDocument();
    });

    it('should show lock icon for locked character', () => {
      const lockedChar = { ...mockCharacter, lockState: 'locked', isLocked: true };
      render(<CharacterCard character={lockedChar} {...mockHandlers} />);
      // Lock icon should be visible in header
      const card = screen.getByText('JOHN').closest('.card');
      expect(card).toHaveClass('border-green-500/30');
    });
  });

  describe('Protagonist Indicator', () => {
    it('should highlight protagonist character', () => {
      render(<CharacterCard character={mockCharacter} {...mockHandlers} />);
      const card = screen.getByText('JOHN').closest('.card');
      expect(card).toHaveClass('ring-2');
    });

    it('should not highlight non-protagonist character', () => {
      const nonProtag = { ...mockCharacter, isProtagonist: false };
      render(<CharacterCard character={nonProtag} {...mockHandlers} />);
      const card = screen.getByText('JOHN').closest('.card');
      expect(card).not.toHaveClass('ring-2');
    });
  });

  describe('Expand/Collapse', () => {
    it('should show "Show more" button', () => {
      render(<CharacterCard character={mockCharacter} {...mockHandlers} />);
      expect(screen.getByText('Show more')).toBeInTheDocument();
    });

    it('should expand when clicking Show more', () => {
      render(<CharacterCard character={mockCharacter} {...mockHandlers} />);
      fireEvent.click(screen.getByText('Show more'));
      expect(screen.getByText('Show less')).toBeInTheDocument();
    });

    it('should show physical description when expanded', () => {
      render(<CharacterCard character={mockCharacter} {...mockHandlers} />);
      fireEvent.click(screen.getByText('Show more'));
      expect(screen.getByText('Physical Description')).toBeInTheDocument();
    });

    it('should start expanded when isExpanded is true', () => {
      render(<CharacterCard character={mockCharacter} {...mockHandlers} isExpanded />);
      expect(screen.getByText('Show less')).toBeInTheDocument();
    });
  });

  describe('Actions - Unlocked Character', () => {
    it('should show Edit Details button when unlocked', () => {
      render(<CharacterCard character={mockCharacter} {...mockHandlers} isExpanded />);
      expect(screen.getByText('Edit Details')).toBeInTheDocument();
    });

    it('should call onEdit when Edit Details clicked', () => {
      render(<CharacterCard character={mockCharacter} {...mockHandlers} isExpanded />);
      fireEvent.click(screen.getByText('Edit Details'));
      expect(mockHandlers.onEdit).toHaveBeenCalledWith(mockCharacter);
    });

    it('should show Add Reference button when unlocked', () => {
      render(<CharacterCard character={mockCharacter} {...mockHandlers} isExpanded />);
      expect(screen.getByText('Add Reference')).toBeInTheDocument();
    });

    it('should call onUploadReference when Add Reference clicked', () => {
      render(<CharacterCard character={mockCharacter} {...mockHandlers} isExpanded />);
      fireEvent.click(screen.getByText('Add Reference'));
      expect(mockHandlers.onUploadReference).toHaveBeenCalledWith('char-1');
    });

    it('should show AI Describe button when unlocked', () => {
      render(<CharacterCard character={mockCharacter} {...mockHandlers} isExpanded />);
      expect(screen.getByText('AI Describe')).toBeInTheDocument();
    });

    it('should call onGenerateDescription when AI Describe clicked', () => {
      render(<CharacterCard character={mockCharacter} {...mockHandlers} isExpanded />);
      fireEvent.click(screen.getByText('AI Describe'));
      expect(mockHandlers.onGenerateDescription).toHaveBeenCalledWith('char-1');
    });

    it('should show Save Look button when unlocked', () => {
      render(<CharacterCard character={mockCharacter} {...mockHandlers} isExpanded />);
      expect(screen.getByText('Save Look')).toBeInTheDocument();
    });

    it('should call onLock when Save Look clicked', () => {
      render(<CharacterCard character={mockCharacter} {...mockHandlers} isExpanded />);
      fireEvent.click(screen.getByText('Save Look'));
      expect(mockHandlers.onLock).toHaveBeenCalledWith('char-1');
    });
  });

  describe('Actions - Locked Character', () => {
    const lockedChar = { ...mockCharacter, lockState: 'locked', isLocked: true };

    it('should show Edit Look button when locked', () => {
      render(<CharacterCard character={lockedChar} {...mockHandlers} isExpanded />);
      expect(screen.getByText('Edit Look')).toBeInTheDocument();
    });

    it('should call onUnlock when Edit Look clicked', () => {
      render(<CharacterCard character={lockedChar} {...mockHandlers} isExpanded />);
      fireEvent.click(screen.getByText('Edit Look'));
      expect(mockHandlers.onUnlock).toHaveBeenCalledWith('char-1');
    });

    it('should not show Edit Details button when locked', () => {
      render(<CharacterCard character={lockedChar} {...mockHandlers} isExpanded />);
      expect(screen.queryByText('Edit Details')).not.toBeInTheDocument();
    });
  });

  describe('Disabled State', () => {
    it('should disable buttons when disabled prop is true', () => {
      render(<CharacterCard character={mockCharacter} {...mockHandlers} isExpanded disabled />);
      expect(screen.getByText('Edit Details').closest('button')).toBeDisabled();
      expect(screen.getByText('Add Reference').closest('button')).toBeDisabled();
    });
  });

  describe('Physical Description Display', () => {
    it('should show hair info when available', () => {
      render(<CharacterCard character={mockCharacter} {...mockHandlers} isExpanded />);
      expect(screen.getByText(/brown/)).toBeInTheDocument();
    });

    it('should show eye color when available', () => {
      render(<CharacterCard character={mockCharacter} {...mockHandlers} isExpanded />);
      expect(screen.getByText(/blue/)).toBeInTheDocument();
    });

    it('should show Edit button for physical description when unlocked', () => {
      render(<CharacterCard character={mockCharacter} {...mockHandlers} isExpanded />);
      expect(screen.getByText('Edit')).toBeInTheDocument();
    });
  });

  describe('Voice Assignment', () => {
    it('should show voice selector for characters with dialogue', () => {
      render(<CharacterCard character={mockCharacter} {...mockHandlers} isExpanded />);
      expect(screen.getByTestId('voice-selector')).toBeInTheDocument();
    });

    it('should not show voice selector for characters without dialogue', () => {
      const noDialogue = { ...mockCharacter, dialogueCount: 0 };
      render(<CharacterCard character={noDialogue} {...mockHandlers} isExpanded />);
      expect(screen.queryByTestId('voice-selector')).not.toBeInTheDocument();
    });
  });

  describe('Reference Assets', () => {
    it('should show reference count', () => {
      render(<CharacterCard character={mockCharacter} {...mockHandlers} />);
      expect(screen.getByText('0 refs')).toBeInTheDocument();
    });

    it('should show reference images when available', () => {
      const charWithRefs = {
        ...mockCharacter,
        referenceAssets: [
          { id: 'ref-1', originalFilename: 'ref.jpg', filePath: '/path/to/ref.jpg', isPrimary: true },
        ],
        referenceCount: 1,
      };
      render(<CharacterCard character={charWithRefs} {...mockHandlers} isExpanded />);
      expect(screen.getByText('Reference Images')).toBeInTheDocument();
    });
  });

  describe('Screenplay Name', () => {
    it('should show screenplay name when different from display name', () => {
      const charWithDiffName = { ...mockCharacter, screenplayName: 'DETECTIVE JOHN' };
      render(<CharacterCard character={charWithDiffName} {...mockHandlers} />);
      expect(screen.getByText('as "DETECTIVE JOHN"')).toBeInTheDocument();
    });

    it('should not show screenplay name when same as display name', () => {
      render(<CharacterCard character={mockCharacter} {...mockHandlers} />);
      expect(screen.queryByText(/as "/)).not.toBeInTheDocument();
    });
  });
});
