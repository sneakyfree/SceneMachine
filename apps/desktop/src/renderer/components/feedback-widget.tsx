/**
 * Feedback Widget Component
 *
 * Provides in-app feedback collection with:
 * - Screenshot capture with annotations
 * - Issue severity selection
 * - Category tagging
 * - Keyboard shortcut (Shift+F)
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';

// Types
interface FeedbackData {
  id: string;
  type: 'bug' | 'feature' | 'improvement' | 'question';
  severity: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  description: string;
  screenshot?: string;
  url: string;
  timestamp: string;
  userAgent: string;
  sessionId?: string;
}

interface FeedbackWidgetProps {
  sessionId?: string;
  onSubmit?: (feedback: FeedbackData) => void;
  position?: 'bottom-right' | 'bottom-left';
}

// Severity colors
const SEVERITY_COLORS = {
  critical: '#EF4444',
  high: '#F97316',
  medium: '#EAB308',
  low: '#22C55E',
};

// Type icons
const TYPE_ICONS = {
  bug: '🐛',
  feature: '✨',
  improvement: '💡',
  question: '❓',
};

export function FeedbackWidget({
  sessionId,
  onSubmit,
  position = 'bottom-right',
}: FeedbackWidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isCapturing, setIsCapturing] = useState(false);
  const [formData, setFormData] = useState<Partial<FeedbackData>>({
    type: 'bug',
    severity: 'medium',
    title: '',
    description: '',
  });
  const [screenshot, setScreenshot] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);

  // Keyboard shortcut: Shift+F
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.shiftKey && e.key.toLowerCase() === 'f') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
      // Escape to close
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  // Capture screenshot
  const captureScreenshot = useCallback(async () => {
    setIsCapturing(true);
    setIsOpen(false); // Hide dialog during capture

    try {
      // Wait for dialog to close
      await new Promise((resolve) => setTimeout(resolve, 100));

      // Use html2canvas if available, otherwise create placeholder
      const html2canvas = (window as any).html2canvas;
      if (html2canvas) {
        const canvas = await html2canvas(document.body, {
          useCORS: true,
          logging: false,
          scale: 1,
        });
        setScreenshot(canvas.toDataURL('image/png'));
      } else {
        // Fallback: create a simple placeholder
        const canvas = document.createElement('canvas');
        canvas.width = 400;
        canvas.height = 300;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.fillStyle = '#1F2937';
          ctx.fillRect(0, 0, 400, 300);
          ctx.fillStyle = '#9CA3AF';
          ctx.font = '14px sans-serif';
          ctx.textAlign = 'center';
          ctx.fillText('Screenshot captured', 200, 150);
          ctx.fillText('(html2canvas not loaded)', 200, 170);
        }
        setScreenshot(canvas.toDataURL('image/png'));
      }
    } catch (error) {
      console.error('Screenshot capture failed:', error);
    } finally {
      setIsCapturing(false);
      setIsOpen(true);
    }
  }, []);

  // Submit feedback
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    const feedback: FeedbackData = {
      id: crypto.randomUUID(),
      type: formData.type as FeedbackData['type'],
      severity: formData.severity as FeedbackData['severity'],
      title: formData.title || '',
      description: formData.description || '',
      screenshot: screenshot || undefined,
      url: window.location.href,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      sessionId,
    };

    try {
      // Send to API
      const response = await fetch('/api/v1/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(feedback),
      });

      if (!response.ok) {
        throw new Error('Failed to submit feedback');
      }

      // Call onSubmit callback
      onSubmit?.(feedback);

      // Show success
      setShowSuccess(true);
      setTimeout(() => {
        setShowSuccess(false);
        setIsOpen(false);
        // Reset form
        setFormData({ type: 'bug', severity: 'medium', title: '', description: '' });
        setScreenshot(null);
      }, 2000);
    } catch (error) {
      console.error('Failed to submit feedback:', error);
      alert('Failed to submit feedback. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Position styles
  const positionStyles =
    position === 'bottom-right'
      ? { right: '1rem', bottom: '1rem' }
      : { left: '1rem', bottom: '1rem' };

  return (
    <>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(true)}
        className="feedback-trigger"
        style={{
          position: 'fixed',
          ...positionStyles,
          zIndex: 9999,
          display: isOpen ? 'none' : 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.75rem 1rem',
          backgroundColor: '#6366F1',
          color: 'white',
          border: 'none',
          borderRadius: '9999px',
          cursor: 'pointer',
          boxShadow: '0 4px 12px rgba(99, 102, 241, 0.4)',
          transition: 'transform 0.2s, box-shadow 0.2s',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'scale(1.05)';
          e.currentTarget.style.boxShadow = '0 6px 16px rgba(99, 102, 241, 0.5)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'scale(1)';
          e.currentTarget.style.boxShadow = '0 4px 12px rgba(99, 102, 241, 0.4)';
        }}
        title="Send Feedback (Shift+F)"
      >
        <span>💬</span>
        <span>Feedback</span>
      </button>

      {/* Feedback Dialog */}
      {isOpen && (
        <div
          className="feedback-overlay"
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            zIndex: 10000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget) setIsOpen(false);
          }}
        >
          <div
            ref={dialogRef}
            className="feedback-dialog"
            style={{
              width: '100%',
              maxWidth: '500px',
              maxHeight: '90vh',
              overflow: 'auto',
              backgroundColor: '#1F2937',
              borderRadius: '0.75rem',
              padding: '1.5rem',
              margin: '1rem',
              boxShadow: '0 20px 50px rgba(0, 0, 0, 0.5)',
            }}
          >
            {/* Header */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '1.5rem',
              }}
            >
              <h2
                style={{
                  margin: 0,
                  fontSize: '1.25rem',
                  fontWeight: 600,
                  color: 'white',
                }}
              >
                Send Feedback
              </h2>
              <button
                onClick={() => setIsOpen(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#9CA3AF',
                  fontSize: '1.5rem',
                  cursor: 'pointer',
                  padding: '0.25rem',
                }}
              >
                ×
              </button>
            </div>

            {showSuccess ? (
              <div
                style={{
                  textAlign: 'center',
                  padding: '2rem',
                  color: '#22C55E',
                }}
              >
                <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>✓</div>
                <p style={{ margin: 0, fontSize: '1.125rem' }}>Thank you for your feedback!</p>
              </div>
            ) : (
              <form onSubmit={handleSubmit}>
                {/* Type Selection */}
                <div style={{ marginBottom: '1rem' }}>
                  <label
                    style={{
                      display: 'block',
                      marginBottom: '0.5rem',
                      color: '#D1D5DB',
                      fontSize: '0.875rem',
                    }}
                  >
                    Type
                  </label>
                  <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                    {(['bug', 'feature', 'improvement', 'question'] as const).map((type) => (
                      <button
                        key={type}
                        type="button"
                        onClick={() => setFormData((prev) => ({ ...prev, type }))}
                        style={{
                          padding: '0.5rem 1rem',
                          borderRadius: '0.5rem',
                          border:
                            formData.type === type ? '2px solid #6366F1' : '1px solid #374151',
                          backgroundColor: formData.type === type ? '#312E81' : 'transparent',
                          color: 'white',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.25rem',
                        }}
                      >
                        <span>{TYPE_ICONS[type]}</span>
                        <span style={{ textTransform: 'capitalize' }}>{type}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Severity Selection */}
                <div style={{ marginBottom: '1rem' }}>
                  <label
                    style={{
                      display: 'block',
                      marginBottom: '0.5rem',
                      color: '#D1D5DB',
                      fontSize: '0.875rem',
                    }}
                  >
                    Severity
                  </label>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    {(['critical', 'high', 'medium', 'low'] as const).map((severity) => (
                      <button
                        key={severity}
                        type="button"
                        onClick={() => setFormData((prev) => ({ ...prev, severity }))}
                        style={{
                          padding: '0.5rem 0.75rem',
                          borderRadius: '0.5rem',
                          border:
                            formData.severity === severity
                              ? `2px solid ${SEVERITY_COLORS[severity]}`
                              : '1px solid #374151',
                          backgroundColor:
                            formData.severity === severity
                              ? `${SEVERITY_COLORS[severity]}20`
                              : 'transparent',
                          color:
                            formData.severity === severity ? SEVERITY_COLORS[severity] : '#9CA3AF',
                          cursor: 'pointer',
                          textTransform: 'capitalize',
                          fontSize: '0.875rem',
                        }}
                      >
                        {severity}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Title */}
                <div style={{ marginBottom: '1rem' }}>
                  <label
                    style={{
                      display: 'block',
                      marginBottom: '0.5rem',
                      color: '#D1D5DB',
                      fontSize: '0.875rem',
                    }}
                  >
                    Title
                  </label>
                  <input
                    type="text"
                    value={formData.title}
                    onChange={(e) => setFormData((prev) => ({ ...prev, title: e.target.value }))}
                    placeholder="Brief summary of the issue"
                    required
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      borderRadius: '0.5rem',
                      border: '1px solid #374151',
                      backgroundColor: '#111827',
                      color: 'white',
                      fontSize: '0.875rem',
                    }}
                  />
                </div>

                {/* Description */}
                <div style={{ marginBottom: '1rem' }}>
                  <label
                    style={{
                      display: 'block',
                      marginBottom: '0.5rem',
                      color: '#D1D5DB',
                      fontSize: '0.875rem',
                    }}
                  >
                    Description
                  </label>
                  <textarea
                    value={formData.description}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, description: e.target.value }))
                    }
                    placeholder="Describe what happened and what you expected"
                    rows={4}
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      borderRadius: '0.5rem',
                      border: '1px solid #374151',
                      backgroundColor: '#111827',
                      color: 'white',
                      fontSize: '0.875rem',
                      resize: 'vertical',
                    }}
                  />
                </div>

                {/* Screenshot */}
                <div style={{ marginBottom: '1.5rem' }}>
                  <label
                    style={{
                      display: 'block',
                      marginBottom: '0.5rem',
                      color: '#D1D5DB',
                      fontSize: '0.875rem',
                    }}
                  >
                    Screenshot
                  </label>
                  {screenshot ? (
                    <div style={{ position: 'relative' }}>
                      <img
                        src={screenshot}
                        alt="Screenshot"
                        style={{
                          width: '100%',
                          borderRadius: '0.5rem',
                          border: '1px solid #374151',
                        }}
                      />
                      <button
                        type="button"
                        onClick={() => setScreenshot(null)}
                        style={{
                          position: 'absolute',
                          top: '0.5rem',
                          right: '0.5rem',
                          backgroundColor: '#EF4444',
                          color: 'white',
                          border: 'none',
                          borderRadius: '0.25rem',
                          padding: '0.25rem 0.5rem',
                          cursor: 'pointer',
                          fontSize: '0.75rem',
                        }}
                      >
                        Remove
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={captureScreenshot}
                      disabled={isCapturing}
                      style={{
                        width: '100%',
                        padding: '1rem',
                        borderRadius: '0.5rem',
                        border: '2px dashed #374151',
                        backgroundColor: 'transparent',
                        color: '#9CA3AF',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '0.5rem',
                      }}
                    >
                      <span>📷</span>
                      <span>{isCapturing ? 'Capturing...' : 'Capture Screenshot'}</span>
                    </button>
                  )}
                </div>

                {/* Submit Button */}
                <button
                  type="submit"
                  disabled={isSubmitting || !formData.title}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    borderRadius: '0.5rem',
                    border: 'none',
                    backgroundColor: isSubmitting ? '#4B5563' : '#6366F1',
                    color: 'white',
                    fontWeight: 600,
                    cursor: isSubmitting ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '0.5rem',
                  }}
                >
                  {isSubmitting ? (
                    <>
                      <span
                        className="spinner"
                        style={{
                          width: '1rem',
                          height: '1rem',
                          border: '2px solid transparent',
                          borderTopColor: 'white',
                          borderRadius: '50%',
                          animation: 'spin 0.8s linear infinite',
                        }}
                      ></span>
                      <span>Submitting...</span>
                    </>
                  ) : (
                    <>
                      <span>📤</span>
                      <span>Submit Feedback</span>
                    </>
                  )}
                </button>

                {/* Keyboard hint */}
                <p
                  style={{
                    marginTop: '1rem',
                    textAlign: 'center',
                    color: '#6B7280',
                    fontSize: '0.75rem',
                  }}
                >
                  Press{' '}
                  <kbd
                    style={{
                      padding: '0.125rem 0.375rem',
                      backgroundColor: '#374151',
                      borderRadius: '0.25rem',
                    }}
                  >
                    Shift+F
                  </kbd>{' '}
                  to toggle feedback
                </p>
              </form>
            )}
          </div>
        </div>
      )}

      {/* Canvas for screenshot */}
      <canvas ref={canvasRef} style={{ display: 'none' }} />

      {/* Spinner animation */}
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </>
  );
}

export default FeedbackWidget;
