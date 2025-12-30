/**
 * Tests for Skeleton loading components.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '../test-utils';
import {
  Skeleton,
  SkeletonText,
  SkeletonTitle,
  SkeletonAvatar,
  SkeletonButton,
  SkeletonShotCard,
  SkeletonQueueJob,
  SkeletonTimelineClip,
  SkeletonScene,
  SkeletonProjectCard,
  SkeletonList,
} from '../../components/skeleton';

describe('Skeleton', () => {
  it('renders with default styles', () => {
    const { container } = render(<Skeleton />);

    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton).toHaveClass('animate-pulse');
    expect(skeleton).toHaveClass('bg-surface-700');
    expect(skeleton).toHaveClass('rounded');
  });

  it('applies custom className', () => {
    const { container } = render(<Skeleton className="w-full h-4" />);

    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton).toHaveClass('w-full');
    expect(skeleton).toHaveClass('h-4');
  });

  it('is hidden from accessibility tree', () => {
    const { container } = render(<Skeleton />);

    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton).toHaveAttribute('aria-hidden', 'true');
  });
});

describe('SkeletonText', () => {
  it('renders with default width', () => {
    const { container } = render(<SkeletonText />);

    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton).toHaveClass('h-4');
    expect(skeleton).toHaveClass('w-full');
  });

  it('applies custom width', () => {
    const { container } = render(<SkeletonText width="w-1/2" />);

    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton).toHaveClass('w-1/2');
  });
});

describe('SkeletonTitle', () => {
  it('renders with correct size', () => {
    const { container } = render(<SkeletonTitle />);

    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton).toHaveClass('h-6');
    expect(skeleton).toHaveClass('w-48');
  });
});

describe('SkeletonAvatar', () => {
  it('renders as circle with default size', () => {
    const { container } = render(<SkeletonAvatar />);

    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton).toHaveClass('rounded-full');
    expect(skeleton).toHaveClass('w-10');
    expect(skeleton).toHaveClass('h-10');
  });

  it('applies custom size', () => {
    const { container } = render(<SkeletonAvatar size="w-16 h-16" />);

    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton).toHaveClass('w-16');
    expect(skeleton).toHaveClass('h-16');
  });
});

describe('SkeletonButton', () => {
  it('renders with button dimensions', () => {
    const { container } = render(<SkeletonButton />);

    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton).toHaveClass('h-9');
    expect(skeleton).toHaveClass('w-24');
    expect(skeleton).toHaveClass('rounded-lg');
  });
});

describe('SkeletonShotCard', () => {
  it('renders video preview placeholder', () => {
    const { container } = render(<SkeletonShotCard />);

    // Should have aspect-video for video preview
    const videoPlaceholder = container.querySelector('.aspect-video');
    expect(videoPlaceholder).toBeInTheDocument();
  });

  it('renders content area with placeholders', () => {
    const { container } = render(<SkeletonShotCard />);

    // Should have multiple skeleton elements
    const skeletons = container.querySelectorAll('[aria-hidden="true"]');
    expect(skeletons.length).toBeGreaterThan(1);
  });

  it('applies custom className', () => {
    const { container } = render(<SkeletonShotCard className="my-custom-class" />);

    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper).toHaveClass('my-custom-class');
  });
});

describe('SkeletonQueueJob', () => {
  it('renders with job row structure', () => {
    const { container } = render(<SkeletonQueueJob />);

    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper).toHaveClass('p-3');
    expect(wrapper).toHaveClass('border');
    expect(wrapper).toHaveClass('rounded-lg');
  });

  it('contains icon placeholder', () => {
    const { container } = render(<SkeletonQueueJob />);

    const iconPlaceholder = container.querySelector('.w-4.h-4');
    expect(iconPlaceholder).toBeInTheDocument();
  });
});

describe('SkeletonTimelineClip', () => {
  it('renders with default width', () => {
    const { container } = render(<SkeletonTimelineClip />);

    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper).toHaveClass('w-32');
    expect(wrapper).toHaveClass('h-16');
  });

  it('applies custom width', () => {
    const { container } = render(<SkeletonTimelineClip width="w-48" />);

    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper).toHaveClass('w-48');
  });
});

describe('SkeletonScene', () => {
  it('renders scene structure with thumbnail', () => {
    const { container } = render(<SkeletonScene />);

    // Scene thumbnail placeholder
    const thumbnail = container.querySelector('.w-8.h-8');
    expect(thumbnail).toBeInTheDocument();
  });

  it('renders title and description placeholders', () => {
    const { container } = render(<SkeletonScene />);

    const wrapper = container.firstChild as HTMLElement;
    // Should have multiple skeleton elements for content
    const skeletons = container.querySelectorAll('[aria-hidden="true"]');
    expect(skeletons.length).toBeGreaterThan(2);
  });
});

describe('SkeletonProjectCard', () => {
  it('renders project thumbnail placeholder', () => {
    const { container } = render(<SkeletonProjectCard />);

    const thumbnail = container.querySelector('.w-16.h-12');
    expect(thumbnail).toBeInTheDocument();
  });

  it('renders project info structure', () => {
    const { container } = render(<SkeletonProjectCard />);

    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper).toHaveClass('p-4');
    expect(wrapper).toHaveClass('rounded-lg');
    expect(wrapper).toHaveClass('border');
  });
});

describe('SkeletonList', () => {
  it('renders default count of items', () => {
    const { container } = render(
      <SkeletonList>
        {(index) => <Skeleton key={index} className="h-10" />}
      </SkeletonList>
    );

    const skeletons = container.querySelectorAll('.h-10');
    expect(skeletons.length).toBe(3); // Default count
  });

  it('renders custom count of items', () => {
    const { container } = render(
      <SkeletonList count={5}>
        {(index) => <Skeleton key={index} className="h-10" />}
      </SkeletonList>
    );

    const skeletons = container.querySelectorAll('.h-10');
    expect(skeletons.length).toBe(5);
  });

  it('has proper accessibility label', () => {
    render(
      <SkeletonList>
        {(index) => <Skeleton key={index} />}
      </SkeletonList>
    );

    expect(screen.getByLabelText('Loading content')).toBeInTheDocument();
  });

  it('applies custom className to container', () => {
    const { container } = render(
      <SkeletonList className="my-custom-list">
        {(index) => <Skeleton key={index} />}
      </SkeletonList>
    );

    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper).toHaveClass('my-custom-list');
  });

  it('provides correct index to render function', () => {
    const { container } = render(
      <SkeletonList count={3}>
        {(index) => <div key={index} data-testid={`item-${index}`} />}
      </SkeletonList>
    );

    expect(screen.getByTestId('item-0')).toBeInTheDocument();
    expect(screen.getByTestId('item-1')).toBeInTheDocument();
    expect(screen.getByTestId('item-2')).toBeInTheDocument();
  });
});

describe('Skeleton Compositions', () => {
  it('can compose multiple skeletons for shot list loading', () => {
    render(
      <SkeletonList count={3}>
        {(index) => <SkeletonShotCard key={index} />}
      </SkeletonList>
    );

    // Should render 3 shot card skeletons
    const videoPlaceholders = document.querySelectorAll('.aspect-video');
    expect(videoPlaceholders.length).toBe(3);
  });

  it('can compose multiple skeletons for queue loading', () => {
    render(
      <SkeletonList count={5}>
        {(index) => <SkeletonQueueJob key={index} />}
      </SkeletonList>
    );

    // Should render 5 queue job skeletons
    const jobRows = document.querySelectorAll('.p-3');
    expect(jobRows.length).toBe(5);
  });

  it('can compose timeline clip skeletons with varying widths', () => {
    const widths = ['w-24', 'w-32', 'w-40'];

    render(
      <div className="flex gap-2">
        {widths.map((width, index) => (
          <SkeletonTimelineClip key={index} width={width} />
        ))}
      </div>
    );

    const clips = document.querySelectorAll('.h-16');
    expect(clips.length).toBe(3);
    expect(clips[0]).toHaveClass('w-24');
    expect(clips[1]).toHaveClass('w-32');
    expect(clips[2]).toHaveClass('w-40');
  });
});
