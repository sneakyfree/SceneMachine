/**
 * Face Injection Panel - IP-Adapter Face Integration
 *
 * Allows users to:
 * - Upload reference images for character faces
 * - Extract face embeddings
 * - Configure face injection strength
 * - Preview consistency across shots
 */

import React, { useState, useCallback } from 'react';

interface FaceEmbedding {
  id: string;
  characterId: string;
  imagePath: string;
  embedding: number[];
  createdAt: string;
}

interface FaceInjectionPanelProps {
  characterId: string;
  characterName: string;
  currentEmbedding?: FaceEmbedding;
  onEmbeddingExtracted?: (embedding: FaceEmbedding) => void;
  onSettingsChange?: (settings: FaceInjectionSettings) => void;
}

interface FaceInjectionSettings {
  enabled: boolean;
  strength: number; // 0-1
  consistencyCheck: boolean;
  fallbackBehavior: 'retry' | 'skip' | 'notify';
}

export const FaceInjectionPanel: React.FC<FaceInjectionPanelProps> = ({
  characterId,
  characterName,
  currentEmbedding,
  onEmbeddingExtracted,
  onSettingsChange,
}) => {
  const [referenceImage, setReferenceImage] = useState<string | null>(
    currentEmbedding?.imagePath || null
  );
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractionStatus, setExtractionStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [settings, setSettings] = useState<FaceInjectionSettings>({
    enabled: true,
    strength: 0.8,
    consistencyCheck: true,
    fallbackBehavior: 'retry',
  });

  const handleImageUpload = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file) return;

      // Create preview URL
      const previewUrl = URL.createObjectURL(file);
      setReferenceImage(previewUrl);

      // Upload to backend
      setIsExtracting(true);
      setExtractionStatus('idle');

      try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('character_id', characterId);

        const response = await fetch('/api/v1/characters/face-embedding', {
          method: 'POST',
          body: formData,
        });

        if (response.ok) {
          const data = await response.json();
          setExtractionStatus('success');
          onEmbeddingExtracted?.({
            id: data.id,
            characterId,
            imagePath: data.image_path,
            embedding: data.embedding,
            createdAt: new Date().toISOString(),
          });
        } else {
          setExtractionStatus('error');
        }
      } catch (error) {
        console.error('Embedding extraction failed:', error);
        setExtractionStatus('error');
      } finally {
        setIsExtracting(false);
      }
    },
    [characterId, onEmbeddingExtracted]
  );

  const handleSettingChange = useCallback(
    <K extends keyof FaceInjectionSettings>(key: K, value: FaceInjectionSettings[K]) => {
      const newSettings = { ...settings, [key]: value };
      setSettings(newSettings);
      onSettingsChange?.(newSettings);
    },
    [settings, onSettingsChange]
  );

  return (
    <div className="face-injection-panel">
      <h3 className="panel-title">
        <span className="icon">🎭</span>
        Face Injection Settings
      </h3>

      {/* Reference Image Upload */}
      <div className="section">
        <label className="section-label">Reference Image</label>
        <div className="image-upload-area">
          {referenceImage ? (
            <div className="preview-container">
              <img src={referenceImage} alt="Reference face" className="preview-image" />
              <div className="preview-overlay">
                <label className="change-btn" htmlFor={`face-upload-${characterId}`}>
                  Change
                </label>
              </div>
              {extractionStatus === 'success' && (
                <div className="status-badge success">✓ Embedding Ready</div>
              )}
              {extractionStatus === 'error' && (
                <div className="status-badge error">✗ Extraction Failed</div>
              )}
            </div>
          ) : (
            <label className="upload-placeholder" htmlFor={`face-upload-${characterId}`}>
              <span className="upload-icon">📷</span>
              <span>Upload face reference for {characterName}</span>
              <span className="hint">Best: Front-facing, well-lit photo</span>
            </label>
          )}
          <input
            type="file"
            id={`face-upload-${characterId}`}
            accept="image/*"
            onChange={handleImageUpload}
            style={{ display: 'none' }}
          />
          {isExtracting && (
            <div className="extraction-overlay">
              <div className="spinner" />
              <span>Extracting face embedding...</span>
            </div>
          )}
        </div>
      </div>

      {/* Injection Settings */}
      <div className="section">
        <div className="setting-row">
          <label className="setting-label">Enable Face Injection</label>
          <input
            type="checkbox"
            checked={settings.enabled}
            onChange={(e) => handleSettingChange('enabled', e.target.checked)}
          />
        </div>

        <div className="setting-row">
          <label className="setting-label">
            Injection Strength
            <span className="value">{Math.round(settings.strength * 100)}%</span>
          </label>
          <input
            type="range"
            min="0"
            max="100"
            value={settings.strength * 100}
            onChange={(e) => handleSettingChange('strength', parseInt(e.target.value) / 100)}
            disabled={!settings.enabled}
          />
        </div>

        <div className="setting-row">
          <label className="setting-label">Consistency Check</label>
          <input
            type="checkbox"
            checked={settings.consistencyCheck}
            onChange={(e) => handleSettingChange('consistencyCheck', e.target.checked)}
            disabled={!settings.enabled}
          />
        </div>

        <div className="setting-row">
          <label className="setting-label">On Failure</label>
          <select
            value={settings.fallbackBehavior}
            onChange={(e) => handleSettingChange('fallbackBehavior', e.target.value as any)}
            disabled={!settings.enabled}
          >
            <option value="retry">Retry generation</option>
            <option value="skip">Skip face injection</option>
            <option value="notify">Notify for review</option>
          </select>
        </div>
      </div>

      {/* Embedding Info */}
      {currentEmbedding && (
        <div className="section embedding-info">
          <div className="info-row">
            <span className="label">Embedding Dimensions:</span>
            <span className="value">{currentEmbedding.embedding.length}</span>
          </div>
          <div className="info-row">
            <span className="label">Created:</span>
            <span className="value">
              {new Date(currentEmbedding.createdAt).toLocaleDateString()}
            </span>
          </div>
        </div>
      )}

      <style>{`
        .face-injection-panel {
          background: var(--bg-secondary, #1a1a2e);
          border-radius: 12px;
          padding: 20px;
        }

        .panel-title {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 16px;
          margin-bottom: 20px;
          color: var(--text-primary, #fff);
        }

        .section {
          margin-bottom: 20px;
        }

        .section-label {
          display: block;
          font-size: 12px;
          color: var(--text-secondary, #888);
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-bottom: 8px;
        }

        .image-upload-area {
          position: relative;
          border-radius: 8px;
          overflow: hidden;
        }

        .upload-placeholder {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 8px;
          padding: 40px 20px;
          background: var(--bg-tertiary, #252540);
          border: 2px dashed var(--border-color, #444);
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.2s;
        }

        .upload-placeholder:hover {
          border-color: var(--accent-color, #6366f1);
          background: rgba(99, 102, 241, 0.1);
        }

        .upload-icon {
          font-size: 32px;
        }

        .hint {
          font-size: 12px;
          color: var(--text-secondary, #888);
        }

        .preview-container {
          position: relative;
        }

        .preview-image {
          width: 100%;
          aspect-ratio: 1;
          object-fit: cover;
          border-radius: 8px;
        }

        .preview-overlay {
          position: absolute;
          inset: 0;
          background: rgba(0, 0, 0, 0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          opacity: 0;
          transition: opacity 0.2s;
        }

        .preview-container:hover .preview-overlay {
          opacity: 1;
        }

        .change-btn {
          padding: 8px 16px;
          background: var(--accent-color, #6366f1);
          color: white;
          border-radius: 6px;
          cursor: pointer;
        }

        .status-badge {
          position: absolute;
          bottom: 8px;
          left: 8px;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: 500;
        }

        .status-badge.success {
          background: rgba(34, 197, 94, 0.2);
          color: #22c55e;
        }

        .status-badge.error {
          background: rgba(239, 68, 68, 0.2);
          color: #ef4444;
        }

        .extraction-overlay {
          position: absolute;
          inset: 0;
          background: rgba(0, 0, 0, 0.8);
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 12px;
          color: white;
        }

        .spinner {
          width: 32px;
          height: 32px;
          border: 3px solid rgba(255, 255, 255, 0.2);
          border-top-color: var(--accent-color, #6366f1);
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        .setting-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 12px 0;
          border-bottom: 1px solid var(--border-color, #333);
        }

        .setting-label {
          font-size: 14px;
          color: var(--text-primary, #fff);
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .setting-label .value {
          color: var(--accent-color, #6366f1);
          font-weight: 500;
        }

        .setting-row input[type="range"] {
          width: 120px;
          accent-color: var(--accent-color, #6366f1);
        }

        .setting-row select {
          padding: 6px 12px;
          background: var(--bg-tertiary, #252540);
          border: 1px solid var(--border-color, #444);
          border-radius: 6px;
          color: var(--text-primary, #fff);
        }

        .embedding-info {
          background: var(--bg-tertiary, #252540);
          border-radius: 8px;
          padding: 12px;
        }

        .info-row {
          display: flex;
          justify-content: space-between;
          font-size: 13px;
          padding: 4px 0;
        }

        .info-row .label {
          color: var(--text-secondary, #888);
        }
      `}</style>
    </div>
  );
};

export default FaceInjectionPanel;
