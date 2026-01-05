/**
 * useUpload Hook
 *
 * Handles file upload with progress tracking.
 */

import { useState, useCallback } from 'react';
import { api } from '../lib/api-client';

export interface UploadState {
  isUploading: boolean;
  progress: number;
  error: string | null;
  videoId: string | null;
}

export interface UseUploadOptions {
  onProgress?: (progress: number) => void;
  onSuccess?: (videoId: string) => void;
  onError?: (error: string) => void;
}

export function useUpload(options: UseUploadOptions = {}) {
  const [state, setState] = useState<UploadState>({
    isUploading: false,
    progress: 0,
    error: null,
    videoId: null,
  });

  const uploadVideo = useCallback(
    async (file: File) => {
      setState({
        isUploading: true,
        progress: 0,
        error: null,
        videoId: null,
      });

      try {
        const result = await api.uploadVideoFile(file, (progress) => {
          setState((prev) => ({ ...prev, progress }));
          options.onProgress?.(progress);
        });

        setState({
          isUploading: false,
          progress: 100,
          error: null,
          videoId: result.video_id,
        });

        options.onSuccess?.(result.video_id);
        return result.video_id;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Upload failed';
        setState({
          isUploading: false,
          progress: 0,
          error: errorMessage,
          videoId: null,
        });
        options.onError?.(errorMessage);
        throw error;
      }
    },
    [options]
  );

  const uploadThumbnail = useCallback(async (videoId: string, file: File) => {
    try {
      const result = await api.uploadThumbnail(videoId, file);
      return result.thumbnail_url;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Thumbnail upload failed';
      setState((prev) => ({ ...prev, error: errorMessage }));
      throw error;
    }
  }, []);

  const reset = useCallback(() => {
    setState({
      isUploading: false,
      progress: 0,
      error: null,
      videoId: null,
    });
  }, []);

  return {
    ...state,
    uploadVideo,
    uploadThumbnail,
    reset,
  };
}

export default useUpload;
