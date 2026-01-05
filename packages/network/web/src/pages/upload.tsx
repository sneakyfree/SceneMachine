/**
 * Upload Page
 *
 * Video upload flow for creators with drag-drop, metadata editing,
 * and publishing options.
 */

'use client';

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore } from '../stores';
import { apiClient, ContentType, MonetizationType } from '../lib/api-client';

type UploadStep = 'select' | 'uploading' | 'details' | 'publishing';

interface UploadState {
  file: File | null;
  progress: number;
  videoId: string | null;
  error: string | null;
}

interface VideoDetails {
  title: string;
  description: string;
  content_type: ContentType;
  tags: string[];
  monetization_type: MonetizationType;
  ticket_price: number;
}

const CONTENT_TYPES: { value: ContentType; label: string }[] = [
  { value: 'FILM', label: 'Film' },
  { value: 'SHORT', label: 'Short Film' },
  { value: 'SERIES', label: 'Series Episode' },
  { value: 'ANIMATION', label: 'Animation' },
  { value: 'MUSIC_VIDEO', label: 'Music Video' },
  { value: 'CLIP', label: 'Clip / Trailer' },
  { value: 'OTHER', label: 'Other' },
];

const MONETIZATION_OPTIONS: { value: MonetizationType; label: string; description: string }[] = [
  { value: 'FREE_AD', label: 'Free with Ads', description: 'Viewers watch for free, you earn from ads' },
  { value: 'FREE_NO_AD', label: 'Free (No Ads)', description: 'Completely free, no revenue' },
  { value: 'PAID', label: 'Pay to Watch', description: 'Set a ticket price for access' },
  { value: 'SUBSCRIBER_ONLY', label: 'Subscribers Only', description: 'Only your subscribers can watch' },
];

export default function UploadPage() {
  const router = useRouter();
  const { user, isAuthenticated } = useAuthStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [step, setStep] = useState<UploadStep>('select');
  const [isDragging, setIsDragging] = useState(false);
  const [upload, setUpload] = useState<UploadState>({
    file: null,
    progress: 0,
    videoId: null,
    error: null,
  });
  const [details, setDetails] = useState<VideoDetails>({
    title: '',
    description: '',
    content_type: 'SHORT',
    tags: [],
    monetization_type: 'FREE_AD',
    ticket_price: 4.99,
  });
  const [tagInput, setTagInput] = useState('');
  const [thumbnail, setThumbnail] = useState<File | null>(null);
  const [thumbnailPreview, setThumbnailPreview] = useState<string | null>(null);
  const [isPublishing, setIsPublishing] = useState(false);

  // Redirect if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login?redirect=/upload');
    }
  }, [isAuthenticated, router]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  }, []);

  const handleFileSelect = async (file: File) => {
    // Validate file type
    if (!file.type.startsWith('video/')) {
      setUpload(prev => ({ ...prev, error: 'Please select a video file' }));
      return;
    }

    // Validate file size (max 10GB)
    const maxSize = 10 * 1024 * 1024 * 1024;
    if (file.size > maxSize) {
      setUpload(prev => ({ ...prev, error: 'File size must be less than 10GB' }));
      return;
    }

    // Set initial title from filename
    const titleFromFile = file.name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
    setDetails(prev => ({ ...prev, title: titleFromFile }));

    setUpload({ file, progress: 0, videoId: null, error: null });
    setStep('uploading');

    try {
      // Start upload
      const response = await apiClient.uploadVideoFile(file, (progress) => {
        setUpload(prev => ({ ...prev, progress }));
      });

      setUpload(prev => ({ ...prev, videoId: response.video_id, progress: 100 }));
      setStep('details');
    } catch (err) {
      setUpload(prev => ({
        ...prev,
        error: err instanceof Error ? err.message : 'Upload failed',
      }));
      setStep('select');
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const handleAddTag = () => {
    const tag = tagInput.trim().toLowerCase();
    if (tag && !details.tags.includes(tag) && details.tags.length < 10) {
      setDetails(prev => ({ ...prev, tags: [...prev.tags, tag] }));
      setTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setDetails(prev => ({
      ...prev,
      tags: prev.tags.filter(t => t !== tagToRemove),
    }));
  };

  const handleThumbnailSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setThumbnail(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setThumbnailPreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handlePublish = async () => {
    if (!upload.videoId || !details.title.trim()) return;

    setIsPublishing(true);
    setStep('publishing');

    try {
      // Update video details
      await apiClient.updateVideo(upload.videoId, {
        title: details.title,
        description: details.description,
        content_type: details.content_type,
        tags: details.tags,
        monetization_type: details.monetization_type,
        ticket_price: details.monetization_type === 'PAID' ? details.ticket_price : undefined,
      });

      // Upload custom thumbnail if provided
      if (thumbnail) {
        await apiClient.uploadThumbnail(upload.videoId, thumbnail);
      }

      // Publish the video
      await apiClient.publishVideo(upload.videoId);

      // Redirect to the video page
      router.push(`/watch/${upload.videoId}`);
    } catch (err) {
      setUpload(prev => ({
        ...prev,
        error: err instanceof Error ? err.message : 'Failed to publish',
      }));
      setStep('details');
    } finally {
      setIsPublishing(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes >= 1024 * 1024 * 1024) {
      return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
    }
    if (bytes >= 1024 * 1024) {
      return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    }
    return `${(bytes / 1024).toFixed(0)} KB`;
  };

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="upload-page">
      {/* Header */}
      <header className="header">
        <Link href="/" className="logo">
          SceneMachine
        </Link>
        <h1>Upload Video</h1>
        <Link href={`/channel/${user?.id}`} className="profile">
          <img src={user?.avatar_url || '/default-avatar.jpg'} alt={user?.display_name} />
        </Link>
      </header>

      <main className="content">
        {/* Step 1: File Selection */}
        {step === 'select' && (
          <div
            className={`drop-zone ${isDragging ? 'dragging' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="video/*"
              onChange={handleFileInputChange}
              hidden
            />

            <div className="drop-icon">
              <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" />
              </svg>
            </div>

            <h2>Drag and drop your video here</h2>
            <p>or click to browse files</p>

            <div className="file-info">
              <span>Supported formats: MP4, MOV, AVI, MKV, WebM</span>
              <span>Maximum file size: 10GB</span>
            </div>

            {upload.error && (
              <div className="error-message" role="alert">
                {upload.error}
              </div>
            )}
          </div>
        )}

        {/* Step 2: Uploading */}
        {step === 'uploading' && upload.file && (
          <div className="uploading-section">
            <div className="file-preview">
              <div className="file-icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <polygon points="23 7 16 12 23 17 23 7" />
                  <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
                </svg>
              </div>
              <div className="file-details">
                <h3>{upload.file.name}</h3>
                <span>{formatFileSize(upload.file.size)}</span>
              </div>
            </div>

            <div className="progress-section">
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${upload.progress}%` }}
                />
              </div>
              <div className="progress-text">
                <span>Uploading...</span>
                <span>{upload.progress.toFixed(0)}%</span>
              </div>
            </div>

            <p className="upload-tip">
              Please keep this page open while your video uploads.
              Processing will begin automatically after upload completes.
            </p>
          </div>
        )}

        {/* Step 3: Video Details */}
        {step === 'details' && (
          <div className="details-section">
            <div className="details-grid">
              {/* Left: Form */}
              <div className="details-form">
                <h2>Video Details</h2>

                {upload.error && (
                  <div className="error-message" role="alert">
                    {upload.error}
                  </div>
                )}

                <div className="form-group">
                  <label htmlFor="title">Title *</label>
                  <input
                    type="text"
                    id="title"
                    value={details.title}
                    onChange={(e) => setDetails(prev => ({ ...prev, title: e.target.value }))}
                    placeholder="Enter video title"
                    maxLength={100}
                    required
                  />
                  <span className="char-count">{details.title.length}/100</span>
                </div>

                <div className="form-group">
                  <label htmlFor="description">Description</label>
                  <textarea
                    id="description"
                    value={details.description}
                    onChange={(e) => setDetails(prev => ({ ...prev, description: e.target.value }))}
                    placeholder="Tell viewers about your video..."
                    rows={5}
                    maxLength={5000}
                  />
                  <span className="char-count">{details.description.length}/5000</span>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="content_type">Content Type</label>
                    <select
                      id="content_type"
                      value={details.content_type}
                      onChange={(e) => setDetails(prev => ({ ...prev, content_type: e.target.value as ContentType }))}
                    >
                      {CONTENT_TYPES.map(ct => (
                        <option key={ct.value} value={ct.value}>{ct.label}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="form-group">
                  <label htmlFor="tags">Tags</label>
                  <div className="tags-input">
                    <div className="tags-list">
                      {details.tags.map(tag => (
                        <span key={tag} className="tag">
                          {tag}
                          <button type="button" onClick={() => handleRemoveTag(tag)}>×</button>
                        </span>
                      ))}
                    </div>
                    <input
                      type="text"
                      id="tags"
                      value={tagInput}
                      onChange={(e) => setTagInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ',') {
                          e.preventDefault();
                          handleAddTag();
                        }
                      }}
                      placeholder={details.tags.length < 10 ? "Add a tag..." : "Max 10 tags"}
                      disabled={details.tags.length >= 10}
                    />
                  </div>
                  <span className="hint">Press Enter or comma to add tags</span>
                </div>

                <div className="form-group">
                  <label>Monetization</label>
                  <div className="monetization-options">
                    {MONETIZATION_OPTIONS.map(option => (
                      <label
                        key={option.value}
                        className={`monetization-option ${details.monetization_type === option.value ? 'selected' : ''}`}
                      >
                        <input
                          type="radio"
                          name="monetization"
                          value={option.value}
                          checked={details.monetization_type === option.value}
                          onChange={(e) => setDetails(prev => ({ ...prev, monetization_type: e.target.value as MonetizationType }))}
                        />
                        <div className="option-content">
                          <span className="option-label">{option.label}</span>
                          <span className="option-description">{option.description}</span>
                        </div>
                      </label>
                    ))}
                  </div>

                  {details.monetization_type === 'PAID' && (
                    <div className="price-input">
                      <label htmlFor="ticket_price">Ticket Price</label>
                      <div className="price-field">
                        <span className="currency">$</span>
                        <input
                          type="number"
                          id="ticket_price"
                          value={details.ticket_price}
                          onChange={(e) => setDetails(prev => ({ ...prev, ticket_price: parseFloat(e.target.value) || 0 }))}
                          min={0.99}
                          max={99.99}
                          step={0.01}
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Right: Thumbnail */}
              <div className="thumbnail-section">
                <h3>Thumbnail</h3>
                <p className="hint">Upload a custom thumbnail or use auto-generated one</p>

                <div className="thumbnail-preview">
                  {thumbnailPreview ? (
                    <img src={thumbnailPreview} alt="Thumbnail preview" />
                  ) : (
                    <div className="thumbnail-placeholder">
                      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                        <circle cx="8.5" cy="8.5" r="1.5" />
                        <polyline points="21 15 16 10 5 21" />
                      </svg>
                      <span>Auto-generated thumbnail</span>
                    </div>
                  )}
                </div>

                <label className="thumbnail-upload-btn">
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleThumbnailSelect}
                    hidden
                  />
                  {thumbnailPreview ? 'Change Thumbnail' : 'Upload Custom Thumbnail'}
                </label>

                <div className="upload-file-info">
                  {upload.file && (
                    <>
                      <strong>{upload.file.name}</strong>
                      <span>{formatFileSize(upload.file.size)}</span>
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="details-actions">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => router.push('/')}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-primary"
                onClick={handlePublish}
                disabled={!details.title.trim() || isPublishing}
              >
                Publish Video
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Publishing */}
        {step === 'publishing' && (
          <div className="publishing-section">
            <div className="publishing-animation">
              <div className="spinner large" />
            </div>
            <h2>Publishing your video...</h2>
            <p>This may take a moment while we process and optimize your video.</p>
          </div>
        )}
      </main>

      <style jsx>{`
        .upload-page {
          min-height: 100vh;
          background: var(--color-bg-primary);
        }

        .header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: var(--space-4) var(--space-6);
          border-bottom: 1px solid var(--color-border);
        }

        .logo {
          font-size: var(--text-xl);
          font-weight: 700;
          background: var(--gradient-primary);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          text-decoration: none;
        }

        .header h1 {
          font-size: var(--text-lg);
          font-weight: 600;
        }

        .profile img {
          width: 36px;
          height: 36px;
          border-radius: 50%;
          object-fit: cover;
        }

        .content {
          max-width: 1200px;
          margin: 0 auto;
          padding: var(--space-8);
        }

        /* Drop Zone */
        .drop-zone {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 400px;
          border: 2px dashed var(--color-border);
          border-radius: var(--radius-xl);
          background: var(--color-bg-secondary);
          cursor: pointer;
          transition: all var(--transition-fast);
        }

        .drop-zone:hover,
        .drop-zone.dragging {
          border-color: var(--color-accent);
          background: var(--color-accent-light);
        }

        .drop-icon {
          color: var(--color-text-tertiary);
          margin-bottom: var(--space-4);
        }

        .drop-zone.dragging .drop-icon {
          color: var(--color-accent);
        }

        .drop-zone h2 {
          font-size: var(--text-xl);
          margin-bottom: var(--space-2);
        }

        .drop-zone p {
          color: var(--color-text-secondary);
          margin-bottom: var(--space-6);
        }

        .file-info {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: var(--space-1);
          font-size: var(--text-sm);
          color: var(--color-text-tertiary);
        }

        .error-message {
          margin-top: var(--space-4);
          padding: var(--space-3) var(--space-4);
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid var(--color-error);
          border-radius: var(--radius-md);
          color: var(--color-error);
          font-size: var(--text-sm);
        }

        /* Uploading */
        .uploading-section {
          max-width: 600px;
          margin: 0 auto;
          text-align: center;
        }

        .file-preview {
          display: flex;
          align-items: center;
          gap: var(--space-4);
          padding: var(--space-4);
          background: var(--color-bg-secondary);
          border-radius: var(--radius-lg);
          margin-bottom: var(--space-6);
        }

        .file-icon {
          color: var(--color-accent);
        }

        .file-details {
          text-align: left;
        }

        .file-details h3 {
          font-size: var(--text-base);
          margin-bottom: var(--space-1);
        }

        .file-details span {
          font-size: var(--text-sm);
          color: var(--color-text-secondary);
        }

        .progress-section {
          margin-bottom: var(--space-4);
        }

        .progress-bar {
          height: 8px;
          background: var(--color-bg-tertiary);
          border-radius: var(--radius-full);
          overflow: hidden;
        }

        .progress-fill {
          height: 100%;
          background: var(--gradient-primary);
          transition: width var(--transition-normal);
        }

        .progress-text {
          display: flex;
          justify-content: space-between;
          margin-top: var(--space-2);
          font-size: var(--text-sm);
          color: var(--color-text-secondary);
        }

        .upload-tip {
          font-size: var(--text-sm);
          color: var(--color-text-tertiary);
        }

        /* Details */
        .details-section {
          background: var(--color-bg-secondary);
          border-radius: var(--radius-xl);
          padding: var(--space-6);
        }

        .details-section h2 {
          font-size: var(--text-xl);
          margin-bottom: var(--space-6);
        }

        .details-grid {
          display: grid;
          grid-template-columns: 1fr 360px;
          gap: var(--space-8);
        }

        @media (max-width: 900px) {
          .details-grid {
            grid-template-columns: 1fr;
          }
        }

        .form-group {
          margin-bottom: var(--space-5);
        }

        .form-group label {
          display: block;
          font-size: var(--text-sm);
          font-weight: 500;
          margin-bottom: var(--space-2);
          color: var(--color-text-secondary);
        }

        .form-group input,
        .form-group textarea,
        .form-group select {
          width: 100%;
          padding: var(--space-3) var(--space-4);
          background: var(--color-bg-tertiary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-md);
          color: var(--color-text-primary);
          font-size: var(--text-base);
        }

        .form-group input:focus,
        .form-group textarea:focus,
        .form-group select:focus {
          border-color: var(--color-accent);
          outline: none;
        }

        .form-group textarea {
          resize: vertical;
        }

        .char-count {
          display: block;
          text-align: right;
          font-size: var(--text-xs);
          color: var(--color-text-muted);
          margin-top: var(--space-1);
        }

        .hint {
          display: block;
          font-size: var(--text-xs);
          color: var(--color-text-muted);
          margin-top: var(--space-1);
        }

        .form-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: var(--space-4);
        }

        /* Tags */
        .tags-input {
          padding: var(--space-2);
          background: var(--color-bg-tertiary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-md);
        }

        .tags-list {
          display: flex;
          flex-wrap: wrap;
          gap: var(--space-2);
          margin-bottom: var(--space-2);
        }

        .tag {
          display: inline-flex;
          align-items: center;
          gap: var(--space-1);
          padding: var(--space-1) var(--space-2);
          background: var(--color-accent-light);
          border-radius: var(--radius-full);
          font-size: var(--text-sm);
          color: var(--color-accent);
        }

        .tag button {
          width: 16px;
          height: 16px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 14px;
          color: var(--color-accent);
        }

        .tags-input input {
          border: none;
          background: transparent;
          padding: var(--space-1);
          width: 100%;
        }

        .tags-input input:focus {
          outline: none;
        }

        /* Monetization */
        .monetization-options {
          display: flex;
          flex-direction: column;
          gap: var(--space-2);
        }

        .monetization-option {
          display: flex;
          align-items: flex-start;
          gap: var(--space-3);
          padding: var(--space-3);
          background: var(--color-bg-tertiary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-md);
          cursor: pointer;
          transition: all var(--transition-fast);
        }

        .monetization-option:hover,
        .monetization-option.selected {
          border-color: var(--color-accent);
        }

        .monetization-option.selected {
          background: var(--color-accent-light);
        }

        .monetization-option input {
          width: 18px;
          height: 18px;
          margin-top: 2px;
          accent-color: var(--color-accent);
        }

        .option-content {
          flex: 1;
        }

        .option-label {
          display: block;
          font-weight: 500;
          margin-bottom: var(--space-1);
        }

        .option-description {
          font-size: var(--text-sm);
          color: var(--color-text-secondary);
        }

        .price-input {
          margin-top: var(--space-4);
          padding: var(--space-4);
          background: var(--color-bg-tertiary);
          border-radius: var(--radius-md);
        }

        .price-field {
          display: flex;
          align-items: center;
          gap: var(--space-2);
        }

        .currency {
          font-size: var(--text-lg);
          font-weight: 500;
        }

        .price-field input {
          width: 120px;
        }

        /* Thumbnail */
        .thumbnail-section {
          position: sticky;
          top: var(--space-8);
        }

        .thumbnail-section h3 {
          font-size: var(--text-base);
          margin-bottom: var(--space-2);
        }

        .thumbnail-preview {
          aspect-ratio: 16 / 9;
          background: var(--color-bg-tertiary);
          border-radius: var(--radius-lg);
          overflow: hidden;
          margin-bottom: var(--space-4);
        }

        .thumbnail-preview img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .thumbnail-placeholder {
          width: 100%;
          height: 100%;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: var(--space-2);
          color: var(--color-text-muted);
        }

        .thumbnail-upload-btn {
          display: block;
          width: 100%;
          padding: var(--space-3);
          background: var(--color-bg-tertiary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-md);
          text-align: center;
          font-weight: 500;
          cursor: pointer;
          transition: all var(--transition-fast);
        }

        .thumbnail-upload-btn:hover {
          border-color: var(--color-accent);
          color: var(--color-accent);
        }

        .upload-file-info {
          margin-top: var(--space-4);
          padding: var(--space-3);
          background: var(--color-bg-tertiary);
          border-radius: var(--radius-md);
          font-size: var(--text-sm);
        }

        .upload-file-info strong {
          display: block;
          margin-bottom: var(--space-1);
          word-break: break-all;
        }

        .upload-file-info span {
          color: var(--color-text-secondary);
        }

        /* Actions */
        .details-actions {
          display: flex;
          justify-content: flex-end;
          gap: var(--space-3);
          margin-top: var(--space-6);
          padding-top: var(--space-6);
          border-top: 1px solid var(--color-border);
        }

        .btn-primary,
        .btn-secondary {
          padding: var(--space-3) var(--space-6);
          border-radius: var(--radius-md);
          font-weight: 600;
          transition: all var(--transition-fast);
        }

        .btn-primary {
          background: var(--gradient-primary);
          color: white;
        }

        .btn-primary:hover:not(:disabled) {
          opacity: 0.9;
        }

        .btn-primary:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .btn-secondary {
          background: var(--color-bg-tertiary);
          color: var(--color-text-primary);
          border: 1px solid var(--color-border);
        }

        .btn-secondary:hover {
          border-color: var(--color-border-light);
        }

        /* Publishing */
        .publishing-section {
          text-align: center;
          padding: var(--space-16) 0;
        }

        .publishing-animation {
          margin-bottom: var(--space-6);
        }

        .spinner.large {
          width: 64px;
          height: 64px;
          border-width: 4px;
          margin: 0 auto;
        }

        .publishing-section h2 {
          font-size: var(--text-xl);
          margin-bottom: var(--space-2);
        }

        .publishing-section p {
          color: var(--color-text-secondary);
        }

        @media (max-width: 640px) {
          .content {
            padding: var(--space-4);
          }

          .drop-zone {
            min-height: 300px;
            padding: var(--space-4);
          }

          .form-row {
            grid-template-columns: 1fr;
          }

          .details-actions {
            flex-direction: column-reverse;
          }

          .btn-primary,
          .btn-secondary {
            width: 100%;
          }
        }
      `}</style>
    </div>
  );
}
