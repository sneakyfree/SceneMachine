/**
 * UI Component exports
 */

// Skeleton loaders
export {
    Skeleton,
    SkeletonText,
    SkeletonAvatar,
    SkeletonCard,
    SkeletonListItem,
    SkeletonTable,
    SkeletonTimeline,
    SkeletonCalendar,
    SkeletonForm,
    SkeletonAssetGrid,
    skeletonStyles,
} from './skeleton';

// Animations
export {
    Animated,
    PageTransition,
    ModalAnimation,
    ListItemAnimation,
    SuccessAnimation,
    ErrorShake,
    LoadingSpinner,
    useAnimation,
    animationStyles,
    additionalAnimationStyles,
} from './animations';
export type { AnimationVariant, AnimationDuration, AnimationConfig } from './animations';

// Enhanced Toast
export {
    ToastProvider,
    ToastContainer,
    useToast,
    toastAnimationStyles,
} from './enhanced-toast';
export type { Toast, ToastType, ToastPosition } from './enhanced-toast';

// Accessibility
export {
    SkipLinks,
    FocusTrap,
    KeyboardShortcutsProvider,
    KeyboardShortcutsHelp,
    LiveRegion,
    VisuallyHidden,
    IconButton,
    useKeyboardShortcut,
    useKeyboardShortcuts,
    useAnnounce,
    useFocusReturn,
    useHighContrast,
    useReducedMotion,
    focusRingStyles,
} from './accessibility';
