/**
 * Share Dialog component.
 *
 * Modal dialog for creating and managing project shares.
 */

import { useState, useCallback } from 'react';
import {
  X,
  Share2,
  Link,
  Mail,
  Copy,
  Check,
  Clock,
  Eye,
  MessageSquare,
  Edit3,
  Trash2,
  Globe,
  Lock,
  Loader2,
  Users,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useTranslation } from '../i18n/use-translation';
import { useSharingStore } from '../stores/sharing-store';
import type { ShareInfo } from '../api/client';

interface ShareDialogProps {
  projectId: string;
  projectName: string;
  isOpen: boolean;
  onClose: () => void;
}

export function ShareDialog({ projectId, projectName, isOpen, onClose }: ShareDialogProps) {
  const { t } = useTranslation();
  const [tab, setTab] = useState<'create' | 'manage'>('create');
  const [isCreating, setIsCreating] = useState(false);
  const [copySuccess, setCopySuccess] = useState(false);
  const [createdShare, setCreatedShare] = useState<{
    shareCode: string;
    shareUrl: string;
  } | null>(null);

  // Form state
  const [permission, setPermission] = useState<'view' | 'comment' | 'edit'>('view');
  const [recipientEmail, setRecipientEmail] = useState('');
  const [recipientName, setRecipientName] = useState('');
  const [message, setMessage] = useState('');
  const [expiresInDays, setExpiresInDays] = useState<number | null>(7);
  const [isPublic, setIsPublic] = useState(false);

  const { shares, isLoadingShares, createShare, revokeShare, fetchShares } = useSharingStore();

  const handleCreate = useCallback(async () => {
    setIsCreating(true);
    try {
      const result = await createShare({
        projectId,
        permission,
        recipientEmail: recipientEmail || undefined,
        recipientName: recipientName || undefined,
        message: message || undefined,
        expiresInDays: expiresInDays ?? undefined,
        isPublic,
      });

      if (result.success && result.shareCode && result.shareUrl) {
        setCreatedShare({
          shareCode: result.shareCode,
          shareUrl: result.shareUrl,
        });
      }
    } catch (error) {
      console.error('Failed to create share:', error);
    } finally {
      setIsCreating(false);
    }
  }, [
    projectId,
    permission,
    recipientEmail,
    recipientName,
    message,
    expiresInDays,
    isPublic,
    createShare,
  ]);

  const handleCopy = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  }, []);

  const handleRevoke = useCallback(
    async (shareId: string) => {
      if (confirm(t('shareDlg.revokeConfirm', 'Are you sure you want to revoke this share?'))) {
        await revokeShare(shareId);
      }
    },
    [revokeShare, t]
  );

  const resetForm = useCallback(() => {
    setRecipientEmail('');
    setRecipientName('');
    setMessage('');
    setExpiresInDays(7);
    setIsPublic(false);
    setCreatedShare(null);
  }, []);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-lg bg-surface-900 border border-surface-700 rounded-xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-surface-800">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-brand-500/20 rounded-lg">
              <Share2 className="w-5 h-5 text-brand-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold">{t('shareDlg.title', 'Share Project')}</h2>
              <p className="text-sm text-surface-400">{projectName}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-surface-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-surface-800">
          <button
            onClick={() => {
              setTab('create');
              resetForm();
            }}
            className={cn(
              'flex-1 px-4 py-3 text-sm font-medium transition-colors',
              tab === 'create'
                ? 'text-brand-400 border-b-2 border-brand-400'
                : 'text-surface-400 hover:text-surface-200'
            )}
          >
            {t('shareDlg.tabCreate', 'Create Share')}
          </button>
          <button
            onClick={() => {
              setTab('manage');
              fetchShares(projectId);
            }}
            className={cn(
              'flex-1 px-4 py-3 text-sm font-medium transition-colors',
              tab === 'manage'
                ? 'text-brand-400 border-b-2 border-brand-400'
                : 'text-surface-400 hover:text-surface-200'
            )}
          >
            {t('shareDlg.tabManage', 'Manage Shares')} ({shares.length})
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {tab === 'create' && !createdShare && (
            <div className="space-y-4">
              {/* Permission Level */}
              <div>
                <label className="block text-sm font-medium text-surface-400 mb-2">
                  {t('shareDlg.permissionLevel', 'Permission Level')}
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {(['view', 'comment', 'edit'] as const).map((perm) => (
                    <button
                      key={perm}
                      onClick={() => setPermission(perm)}
                      className={cn(
                        'flex flex-col items-center gap-1 px-3 py-3 rounded-lg border transition-colors',
                        permission === perm
                          ? 'border-brand-500 bg-brand-500/10 text-brand-300'
                          : 'border-surface-700 bg-surface-800 text-surface-400 hover:border-surface-600'
                      )}
                    >
                      {perm === 'view' && <Eye className="w-5 h-5" />}
                      {perm === 'comment' && <MessageSquare className="w-5 h-5" />}
                      {perm === 'edit' && <Edit3 className="w-5 h-5" />}
                      <span className="text-xs capitalize">
                        {perm === 'view' && t('shareDlg.permView', 'view')}
                        {perm === 'comment' && t('shareDlg.permComment', 'comment')}
                        {perm === 'edit' && t('shareDlg.permEdit', 'edit')}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Recipient Email */}
              <div>
                <label className="block text-sm font-medium text-surface-400 mb-2">
                  {t('shareDlg.recipientEmail', 'Recipient Email (optional)')}
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-500" />
                  <input
                    type="email"
                    value={recipientEmail}
                    onChange={(e) => setRecipientEmail(e.target.value)}
                    placeholder="recipient@example.com"
                    className="w-full pl-10 pr-4 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm focus:outline-none focus:border-brand-500"
                  />
                </div>
              </div>

              {/* Recipient Name */}
              <div>
                <label className="block text-sm font-medium text-surface-400 mb-2">
                  {t('shareDlg.recipientName', 'Recipient Name (optional)')}
                </label>
                <input
                  type="text"
                  value={recipientName}
                  onChange={(e) => setRecipientName(e.target.value)}
                  placeholder={t('shareDlg.recipientNamePlaceholder', 'John Doe')}
                  className="w-full px-4 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm focus:outline-none focus:border-brand-500"
                />
              </div>

              {/* Expiration */}
              <div>
                <label className="block text-sm font-medium text-surface-400 mb-2">
                  {t('shareDlg.linkExpiration', 'Link Expiration')}
                </label>
                <select
                  value={expiresInDays ?? 'never'}
                  onChange={(e) =>
                    setExpiresInDays(e.target.value === 'never' ? null : parseInt(e.target.value))
                  }
                  className="w-full px-4 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm focus:outline-none focus:border-brand-500"
                >
                  <option value="1">{t('shareDlg.expire1Day', '1 day')}</option>
                  <option value="7">{t('shareDlg.expire7Days', '7 days')}</option>
                  <option value="30">{t('shareDlg.expire30Days', '30 days')}</option>
                  <option value="90">{t('shareDlg.expire90Days', '90 days')}</option>
                  <option value="never">{t('shareDlg.expireNever', 'Never expires')}</option>
                </select>
              </div>

              {/* Public Toggle */}
              <div className="flex items-center justify-between p-3 bg-surface-800 rounded-lg">
                <div className="flex items-center gap-2">
                  {isPublic ? (
                    <Globe className="w-5 h-5 text-green-400" />
                  ) : (
                    <Lock className="w-5 h-5 text-surface-500" />
                  )}
                  <div>
                    <div className="text-sm font-medium">
                      {isPublic
                        ? t('shareDlg.publicLink', 'Public Link')
                        : t('shareDlg.privateLink', 'Private Link')}
                    </div>
                    <div className="text-xs text-surface-500">
                      {isPublic
                        ? t('shareDlg.publicLinkDesc', 'Anyone with the link can access')
                        : t('shareDlg.privateLinkDesc', 'Only invited recipients can access')}
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => setIsPublic(!isPublic)}
                  className={cn(
                    'relative w-11 h-6 rounded-full transition-colors',
                    isPublic ? 'bg-brand-600' : 'bg-surface-600'
                  )}
                >
                  <span
                    className={cn(
                      'absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform',
                      isPublic && 'translate-x-5'
                    )}
                  />
                </button>
              </div>

              {/* Create Button */}
              <button
                onClick={handleCreate}
                disabled={isCreating}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-brand-600 hover:bg-brand-500 text-white font-medium rounded-lg transition-colors disabled:opacity-50"
              >
                {isCreating ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    {t('shareDlg.creating', 'Creating...')}
                  </>
                ) : (
                  <>
                    <Share2 className="w-4 h-4" />
                    {t('shareDlg.createShareLink', 'Create Share Link')}
                  </>
                )}
              </button>
            </div>
          )}

          {tab === 'create' && createdShare && (
            <div className="space-y-4">
              <div className="text-center py-4">
                <div className="w-16 h-16 mx-auto mb-4 bg-green-500/20 rounded-full flex items-center justify-center">
                  <Check className="w-8 h-8 text-green-400" />
                </div>
                <h3 className="text-lg font-semibold mb-1">
                  {t('shareDlg.shareLinkCreated', 'Share Link Created!')}
                </h3>
                <p className="text-sm text-surface-400">
                  {t('shareDlg.copyLinkBelow', 'Copy the link below to share this project')}
                </p>
              </div>

              {/* Share URL */}
              <div className="p-3 bg-surface-800 rounded-lg">
                <div className="text-xs text-surface-500 mb-1">{t('shareDlg.shareLinkLabel', 'Share Link')}</div>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={createdShare.shareUrl}
                    readOnly
                    className="flex-1 px-3 py-2 bg-surface-700 border border-surface-600 rounded text-sm font-mono"
                  />
                  <button
                    onClick={() => handleCopy(createdShare.shareUrl)}
                    className="p-2 bg-brand-600 hover:bg-brand-500 rounded transition-colors"
                  >
                    {copySuccess ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Share Code */}
              <div className="p-3 bg-surface-800 rounded-lg">
                <div className="text-xs text-surface-500 mb-1">{t('shareDlg.shareCodeLabel', 'Share Code')}</div>
                <div className="flex items-center gap-2">
                  <code className="flex-1 px-3 py-2 bg-surface-700 border border-surface-600 rounded text-sm font-mono text-center">
                    {createdShare.shareCode}
                  </code>
                  <button
                    onClick={() => handleCopy(createdShare.shareCode)}
                    className="p-2 bg-surface-700 hover:bg-surface-600 rounded transition-colors"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                </div>
              </div>

              <button
                onClick={resetForm}
                className="w-full px-4 py-2 text-sm text-surface-400 hover:text-surface-200 transition-colors"
              >
                {t('shareDlg.createAnother', 'Create Another Share')}
              </button>
            </div>
          )}

          {tab === 'manage' && (
            <div>
              {isLoadingShares ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-surface-500" />
                </div>
              ) : shares.length === 0 ? (
                <div className="text-center py-8">
                  <Users className="w-12 h-12 mx-auto text-surface-600 mb-3" />
                  <h3 className="text-lg font-medium mb-1">
                    {t('shareDlg.noActiveShares', 'No Active Shares')}
                  </h3>
                  <p className="text-sm text-surface-400">
                    {t('shareDlg.noSharesDesc', 'Create a share link to collaborate with others')}
                  </p>
                </div>
              ) : (
                <div className="space-y-3 max-h-64 overflow-y-auto">
                  {shares.map((share) => (
                    <ShareListItem
                      key={share.id}
                      share={share}
                      onRevoke={() => handleRevoke(share.id)}
                    />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface ShareListItemProps {
  share: ShareInfo;
  onRevoke: () => void;
}

function ShareListItem({ share, onRevoke }: ShareListItemProps) {
  const { t } = useTranslation();
  const getPermissionIcon = (permission: string) => {
    switch (permission) {
      case 'view':
        return <Eye className="w-4 h-4" />;
      case 'comment':
        return <MessageSquare className="w-4 h-4" />;
      case 'edit':
        return <Edit3 className="w-4 h-4" />;
      default:
        return <Eye className="w-4 h-4" />;
    }
  };

  return (
    <div className="flex items-center gap-3 p-3 bg-surface-800 rounded-lg">
      <div
        className={cn(
          'p-2 rounded-lg',
          share.isPublic ? 'bg-green-500/20 text-green-400' : 'bg-brand-500/20 text-brand-400'
        )}
      >
        {share.isPublic ? <Globe className="w-4 h-4" /> : <Link className="w-4 h-4" />}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          {share.recipientName || share.recipientEmail ? (
            <span className="text-sm font-medium truncate">
              {share.recipientName || share.recipientEmail}
            </span>
          ) : (
            <span className="text-sm text-surface-400 italic">{t('shareDlg.publicLinkItem', 'Public link')}</span>
          )}
          <span
            className={cn(
              'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs',
              'bg-surface-700 text-surface-300'
            )}
          >
            {getPermissionIcon(share.permission)}
            {share.permission}
          </span>
        </div>
        <div className="flex items-center gap-3 text-xs text-surface-500 mt-0.5">
          <span>{t('shareDlg.codePrefix', 'Code:')} {share.shareCode}</span>
          {share.expiresAt && (
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {t('shareDlg.expiresPrefix', 'Expires')} {new Date(share.expiresAt).toLocaleDateString()}
            </span>
          )}
          <span>{share.accessCount} {t('shareDlg.viewsSuffix', 'views')}</span>
        </div>
      </div>

      <button
        onClick={onRevoke}
        className="p-2 text-surface-500 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
        title={t('shareDlg.revokeTitle', 'Revoke share')}
      >
        <Trash2 className="w-4 h-4" />
      </button>
    </div>
  );
}
