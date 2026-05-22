/**
 * Animation Utilities
 * Transition animations with spring physics
 */

import React from 'react';
import { cn } from '../../lib/utils';

// Animation variants
export type AnimationVariant =
  | 'fadeIn'
  | 'fadeOut'
  | 'slideUp'
  | 'slideDown'
  | 'slideLeft'
  | 'slideRight'
  | 'scaleIn'
  | 'scaleOut'
  | 'spring'
  | 'bounce';

// Animation duration presets
export type AnimationDuration = 'fast' | 'normal' | 'slow';

const DURATIONS: Record<AnimationDuration, number> = {
  fast: 150,
  normal: 300,
  slow: 500,
};

// Animation config
export interface AnimationConfig {
  variant: AnimationVariant;
  duration?: AnimationDuration | number;
  delay?: number;
  easing?: string;
}

// CSS keyframes for animations
export const animationStyles = `
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes fadeOut {
  from { opacity: 1; }
  to { opacity: 0; }
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes slideDown {
  from { opacity: 0; transform: translateY(-20px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes slideLeft {
  from { opacity: 0; transform: translateX(20px); }
  to { opacity: 1; transform: translateX(0); }
}

@keyframes slideRight {
  from { opacity: 0; transform: translateX(-20px); }
  to { opacity: 1; transform: translateX(0); }
}

@keyframes scaleIn {
  from { opacity: 0; transform: scale(0.9); }
  to { opacity: 1; transform: scale(1); }
}

@keyframes scaleOut {
  from { opacity: 1; transform: scale(1); }
  to { opacity: 0; transform: scale(0.9); }
}

@keyframes spring {
  0% { opacity: 0; transform: scale(0.8); }
  50% { transform: scale(1.05); }
  75% { transform: scale(0.97); }
  100% { opacity: 1; transform: scale(1); }
}

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-5px); }
  75% { transform: translateX(5px); }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
`;

// Animated wrapper component
export const Animated: React.FC<{
  children: React.ReactNode;
  animation: AnimationVariant;
  duration?: AnimationDuration | number;
  delay?: number;
  className?: string;
  onAnimationEnd?: () => void;
}> = ({ children, animation, duration = 'normal', delay = 0, className, onAnimationEnd }) => {
  const durationMs = typeof duration === 'number' ? duration : DURATIONS[duration];

  return (
    <div
      className={className}
      style={{
        animation: `${animation} ${durationMs}ms ease-out forwards`,
        animationDelay: `${delay}ms`,
      }}
      onAnimationEnd={onAnimationEnd}
    >
      {children}
    </div>
  );
};

// Page transition component
export const PageTransition: React.FC<{
  children: React.ReactNode;
  className?: string;
}> = ({ children, className }) => (
  <Animated animation="fadeIn" duration="normal" className={className}>
    {children}
  </Animated>
);

// Modal animation wrapper
export const ModalAnimation: React.FC<{
  children: React.ReactNode;
  isOpen: boolean;
  onClose?: () => void;
  className?: string;
}> = ({ children, isOpen, onClose, className }) => {
  const [shouldRender, setShouldRender] = React.useState(isOpen);

  React.useEffect(() => {
    if (isOpen) setShouldRender(true);
  }, [isOpen]);

  const handleAnimationEnd = () => {
    if (!isOpen) {
      setShouldRender(false);
    }
  };

  if (!shouldRender) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className={cn(
          'fixed inset-0 bg-black/50 z-40',
          isOpen ? 'animate-fadeIn' : 'animate-fadeOut'
        )}
        onClick={onClose}
        style={{
          animationDuration: '200ms',
          animationFillMode: 'forwards',
        }}
      />
      {/* Content */}
      <div
        className={cn('fixed inset-0 z-50 flex items-center justify-center p-4', className)}
        style={{
          animation: `${isOpen ? 'scaleIn' : 'scaleOut'} 200ms ease-out forwards`,
        }}
        onAnimationEnd={handleAnimationEnd}
      >
        {children}
      </div>
    </>
  );
};

// List item animation (staggered)
export const ListItemAnimation: React.FC<{
  children: React.ReactNode;
  index: number;
  staggerDelay?: number;
  className?: string;
}> = ({ children, index, staggerDelay = 50, className }) => (
  <Animated
    animation="slideUp"
    duration="normal"
    delay={index * staggerDelay}
    className={className}
  >
    {children}
  </Animated>
);

// Success animation
export const SuccessAnimation: React.FC<{
  onComplete?: () => void;
  className?: string;
}> = ({ onComplete, className }) => (
  <Animated
    animation="spring"
    duration={500}
    onAnimationEnd={onComplete}
    className={cn(
      'w-16 h-16 rounded-full bg-green-500 flex items-center justify-center',
      className
    )}
  >
    <svg
      className="w-8 h-8 text-white"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="3"
    >
      <path
        d="M5 13l4 4L19 7"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="animate-draw-check"
        style={{
          strokeDasharray: 24,
          strokeDashoffset: 24,
          animation: 'drawCheck 0.3s ease-out 0.2s forwards',
        }}
      />
    </svg>
  </Animated>
);

// Error shake animation
export const ErrorShake: React.FC<{
  children: React.ReactNode;
  trigger?: boolean;
  className?: string;
}> = ({ children, trigger, className }) => {
  const [isShaking, setIsShaking] = React.useState(false);

  React.useEffect(() => {
    if (trigger) {
      setIsShaking(true);
      setTimeout(() => setIsShaking(false), 500);
    }
  }, [trigger]);

  return (
    <div
      className={className}
      style={isShaking ? { animation: 'shake 0.5s ease-in-out' } : undefined}
    >
      {children}
    </div>
  );
};

// Loading spinner with fade
export const LoadingSpinner: React.FC<{
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}> = ({ size = 'md', className }) => {
  const sizes = { sm: 16, md: 24, lg: 32 };
  return (
    <div
      className={cn('text-brand-500', className)}
      style={{
        width: sizes[size],
        height: sizes[size],
        animation: 'spin 1s linear infinite, fadeIn 0.2s ease-out',
      }}
    >
      <svg viewBox="0 0 24 24" fill="none" className="w-full h-full">
        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity="0.25" />
        <path
          d="M12 2a10 10 0 0 1 10 10"
          stroke="currentColor"
          strokeWidth="3"
          strokeLinecap="round"
        />
      </svg>
    </div>
  );
};

// Hook for triggering animations
export function useAnimation(initialState = false) {
  const [isAnimating, setIsAnimating] = React.useState(initialState);
  const [animationKey, setAnimationKey] = React.useState(0);

  const trigger = React.useCallback(() => {
    setAnimationKey((k) => k + 1);
    setIsAnimating(true);
  }, []);

  const reset = React.useCallback(() => {
    setIsAnimating(false);
  }, []);

  return { isAnimating, animationKey, trigger, reset };
}

// Additional CSS for custom animations
export const additionalAnimationStyles = `
@keyframes drawCheck {
  to { stroke-dashoffset: 0; }
}

.animate-fadeIn { animation: fadeIn 0.2s ease-out forwards; }
.animate-fadeOut { animation: fadeOut 0.2s ease-out forwards; }
.animate-slideUp { animation: slideUp 0.3s ease-out forwards; }
.animate-slideDown { animation: slideDown 0.3s ease-out forwards; }
.animate-scaleIn { animation: scaleIn 0.2s ease-out forwards; }
.animate-spring { animation: spring 0.5s ease-out forwards; }
.animate-bounce { animation: bounce 0.5s ease-in-out infinite; }
.animate-pulse { animation: pulse 1.5s ease-in-out infinite; }
.animate-spin { animation: spin 1s linear infinite; }
`;
