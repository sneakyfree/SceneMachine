/**
 * Timeline component exports.
 */

export { ClipContextMenu } from './clip-context-menu';
export { LipSyncQuickModal } from './lipsync-quick-modal';
export { TransitionPicker, TransitionZone } from './transition-picker';
export type { TransitionType, TransitionConfig } from './transition-picker';

// Audio drag-drop components
export { DraggableAudioItem } from './draggable-audio-item';
export type { AudioItem } from './draggable-audio-item';
export { TimelineDropZone } from './timeline-drop-zone';
export { AudioLibraryPanel } from './audio-library-panel';

// Track layers and management
export { TimelineTrackLayers, useTimelineTracks } from './timeline-track-layers';
export type { Track, TrackType } from './timeline-track-layers';

// Zoom, pan, and minimap
export { TimelineMinimap, useTimelineViewport } from './timeline-minimap';

// Clip editing
export { ClipTrimmerSplitter, useClipEditor } from './clip-trimmer-splitter';
