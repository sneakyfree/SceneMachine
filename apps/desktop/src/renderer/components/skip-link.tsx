/**
 * Skip link for keyboard navigation accessibility.
 * Allows users to skip directly to main content.
 */

interface SkipLinkProps {
  targetId?: string;
  children?: React.ReactNode;
}

export function SkipLink({
  targetId = 'main-content',
  children = 'Skip to main content',
}: SkipLinkProps) {
  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    const target = document.getElementById(targetId);
    if (target) {
      target.tabIndex = -1;
      target.focus();
      target.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <a
      href={`#${targetId}`}
      onClick={handleClick}
      className="
        sr-only focus:not-sr-only
        fixed top-0 left-0 z-[100]
        px-4 py-2 m-2
        bg-brand-500 text-white
        font-medium rounded-lg
        focus:outline-none focus:ring-2 focus:ring-brand-400 focus:ring-offset-2 focus:ring-offset-surface-950
        transition-transform transform -translate-y-full focus:translate-y-0
      "
    >
      {children}
    </a>
  );
}
