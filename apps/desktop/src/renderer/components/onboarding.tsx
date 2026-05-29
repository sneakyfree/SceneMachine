/**
 * Onboarding flow for new users.
 * Guides users through initial setup and configuration.
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Film,
  Key,
  Sparkles,
  ArrowRight,
  ArrowLeft,
  Check,
  Upload,
  Users,
  Clapperboard,
  Video,
  Eye,
  EyeOff,
  Loader2,
  AlertCircle,
  X,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useSettingsStore } from '../stores/settings-store';
import { useTranslation } from '../i18n/use-translation';

interface OnboardingProps {
  onComplete: () => void;
  onSkip?: () => void;
}

// Step indicator
function StepIndicator({
  currentStep,
  totalSteps,
  stepTitles,
}: {
  currentStep: number;
  totalSteps: number;
  stepTitles: string[];
}) {
  return (
    <div className="flex items-center justify-center gap-2">
      {Array.from({ length: totalSteps }, (_, i) => (
        <div key={i} className="flex items-center gap-2">
          <div
            className={cn(
              'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors',
              i < currentStep
                ? 'bg-brand-500 text-white'
                : i === currentStep
                  ? 'bg-brand-500/20 text-brand-400 border-2 border-brand-500'
                  : 'bg-surface-700 text-surface-400'
            )}
          >
            {i < currentStep ? <Check className="w-4 h-4" /> : i + 1}
          </div>
          {i < totalSteps - 1 && (
            <div
              className={cn(
                'w-12 h-0.5 transition-colors',
                i < currentStep ? 'bg-brand-500' : 'bg-surface-700'
              )}
            />
          )}
        </div>
      ))}
    </div>
  );
}

// Welcome step
function WelcomeStep({ onNext }: { onNext: () => void }) {
  const { t } = useTranslation();
  return (
    <div className="text-center max-w-lg mx-auto">
      <div className="w-20 h-20 bg-brand-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
        <Film className="w-10 h-10 text-brand-400" />
      </div>

      <h2 className="text-2xl font-bold mb-4">
        {t('onboarding.welcomeTitle', 'Welcome to SceneMachine')}
      </h2>

      <p className="text-surface-300 mb-8">
        {t(
          'onboarding.welcomeDescription',
          "Transform your screenplays into stunning video content using AI-powered generation. Let's get you set up in just a few steps."
        )}
      </p>

      {/* Feature highlights */}
      <div className="grid grid-cols-2 gap-4 mb-8 text-left">
        <div className="p-4 bg-surface-800/50 rounded-lg">
          <Upload className="w-6 h-6 text-brand-400 mb-2" />
          <h4 className="font-medium mb-1">
            {t('onboarding.featureUploadTitle', 'Upload Screenplays')}
          </h4>
          <p className="text-sm text-surface-400">
            {t('onboarding.featureUploadDescription', 'Import Fountain or Final Draft files directly')}
          </p>
        </div>
        <div className="p-4 bg-surface-800/50 rounded-lg">
          <Users className="w-6 h-6 text-brand-400 mb-2" />
          <h4 className="font-medium mb-1">
            {t('onboarding.featureCharactersTitle', 'Manage Characters')}
          </h4>
          <p className="text-sm text-surface-400">
            {t('onboarding.featureCharactersDescription', 'Define appearances, assign voices, lock designs')}
          </p>
        </div>
        <div className="p-4 bg-surface-800/50 rounded-lg">
          <Clapperboard className="w-6 h-6 text-brand-400 mb-2" />
          <h4 className="font-medium mb-1">
            {t('onboarding.featureShotsTitle', 'Plan Shots')}
          </h4>
          <p className="text-sm text-surface-400">
            {t('onboarding.featureShotsDescription', 'AI-assisted shot breakdown and composition')}
          </p>
        </div>
        <div className="p-4 bg-surface-800/50 rounded-lg">
          <Video className="w-6 h-6 text-brand-400 mb-2" />
          <h4 className="font-medium mb-1">
            {t('onboarding.featureVideoTitle', 'Generate Video')}
          </h4>
          <p className="text-sm text-surface-400">
            {t('onboarding.featureVideoDescription', 'Create and export professional video content')}
          </p>
        </div>
      </div>

      <button
        onClick={onNext}
        className="px-6 py-3 bg-brand-500 hover:bg-brand-600 rounded-lg font-medium flex items-center gap-2 mx-auto"
      >
        {t('onboarding.getStarted', 'Get Started')}
        <ArrowRight className="w-5 h-5" />
      </button>
    </div>
  );
}

// API Keys step
function ApiKeysStep({ onNext, onBack }: { onNext: () => void; onBack: () => void }) {
  const { t } = useTranslation();
  const { settings, setApiKey, validateApiKey, isSaving, fetchSettings } = useSettingsStore();

  const [anthropicKey, setAnthropicKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [validationStatus, setValidationStatus] = useState<
    'idle' | 'validating' | 'valid' | 'invalid'
  >('idle');
  const [validationMessage, setValidationMessage] = useState('');

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleValidate = async () => {
    if (!anthropicKey.trim()) return;

    setValidationStatus('validating');
    try {
      const result = await validateApiKey('anthropic', anthropicKey);
      if (result.available) {
        setValidationStatus('valid');
        setValidationMessage(result.message);
      } else {
        setValidationStatus('invalid');
        setValidationMessage(result.message);
      }
    } catch (error) {
      setValidationStatus('invalid');
      setValidationMessage(t('onboarding.validateFailed', 'Failed to validate API key'));
    }
  };

  const handleSave = async () => {
    if (!anthropicKey.trim()) {
      onNext();
      return;
    }

    try {
      await setApiKey('anthropic', anthropicKey);
      onNext();
    } catch (error) {
      console.error('Failed to save API key:', error);
    }
  };

  const isAnthropicConfigured = settings?.apiKeys?.anthropic?.configured;

  return (
    <div className="max-w-lg mx-auto">
      <div className="text-center mb-8">
        <div className="w-16 h-16 bg-brand-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
          <Key className="w-8 h-8 text-brand-400" />
        </div>
        <h2 className="text-2xl font-bold mb-2">
          {t('onboarding.apiKeysTitle', 'Configure API Keys')}
        </h2>
        <p className="text-surface-400">
          {t(
            'onboarding.apiKeysDescription',
            'SceneMachine uses AI services to analyze screenplays and generate content.'
          )}
        </p>
      </div>

      {/* Anthropic API Key */}
      <div className="space-y-4 mb-8">
        <div>
          <label className="block text-sm font-medium mb-2">
            {t('onboarding.anthropicKeyLabel', 'Anthropic API Key')}{' '}
            <span className="text-surface-400 font-normal">
              {t('onboarding.anthropicKeyRequired', '(Required for screenplay analysis)')}
            </span>
          </label>

          {isAnthropicConfigured ? (
            <div className="p-4 bg-green-500/10 border border-green-500/30 rounded-lg flex items-center gap-3">
              <Check className="w-5 h-5 text-green-400" />
              <div>
                <p className="font-medium text-green-400">
                  {t('onboarding.apiKeyConfigured', 'API Key Configured')}
                </p>
                <p className="text-sm text-surface-400">
                  {t('onboarding.apiKeyMasked', 'Masked:')} {settings?.apiKeys?.anthropic?.masked}
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="relative">
                <input
                  type={showKey ? 'text' : 'password'}
                  value={anthropicKey}
                  onChange={(e) => {
                    setAnthropicKey(e.target.value);
                    setValidationStatus('idle');
                  }}
                  placeholder="sk-ant-..."
                  className="w-full bg-surface-800 border border-surface-700 rounded-lg px-4 py-3 pr-20"
                />
                <button
                  type="button"
                  onClick={() => setShowKey(!showKey)}
                  className="absolute right-12 top-1/2 -translate-y-1/2 text-surface-400 hover:text-surface-300 p-1"
                >
                  {showKey ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
                <button
                  type="button"
                  onClick={handleValidate}
                  disabled={!anthropicKey.trim() || validationStatus === 'validating'}
                  className="absolute right-2 top-1/2 -translate-y-1/2 px-2 py-1 text-sm text-brand-400 hover:text-brand-300 disabled:opacity-50"
                >
                  {validationStatus === 'validating' ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    t('onboarding.test', 'Test')
                  )}
                </button>
              </div>

              {validationStatus !== 'idle' && validationStatus !== 'validating' && (
                <div
                  className={cn(
                    'flex items-center gap-2 px-3 py-2 rounded-lg text-sm',
                    validationStatus === 'valid'
                      ? 'bg-green-500/10 text-green-400'
                      : 'bg-red-500/10 text-red-400'
                  )}
                >
                  {validationStatus === 'valid' ? (
                    <Check className="w-4 h-4" />
                  ) : (
                    <AlertCircle className="w-4 h-4" />
                  )}
                  {validationMessage}
                </div>
              )}

              <p className="text-xs text-surface-400">
                {t('onboarding.getApiKeyFrom', 'Get your API key from')}{' '}
                <a
                  href="https://console.anthropic.com/settings/keys"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-brand-400 hover:text-brand-300"
                >
                  console.anthropic.com
                </a>
              </p>
            </div>
          )}
        </div>

        <div className="p-4 bg-surface-800/50 rounded-lg">
          <p className="text-sm text-surface-400">
            <strong className="text-surface-200">{t('onboarding.noteLabel', 'Note:')}</strong>{' '}
            {t(
              'onboarding.noteText',
              'You can configure additional providers (OpenAI, ElevenLabs, etc.) later in Settings.'
            )}
          </p>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="px-4 py-2 text-surface-400 hover:text-surface-200 flex items-center gap-2"
        >
          <ArrowLeft className="w-5 h-5" />
          {t('onboarding.back', 'Back')}
        </button>
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="px-6 py-3 bg-brand-500 hover:bg-brand-600 rounded-lg font-medium flex items-center gap-2 disabled:opacity-50"
        >
          {isSaving ? <Loader2 className="w-5 h-5 animate-spin" /> : null}
          {anthropicKey.trim()
            ? t('onboarding.saveContinue', 'Save & Continue')
            : t('onboarding.skipForNow', 'Skip for Now')}
          <ArrowRight className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}

// Workflow overview step
function WorkflowStep({ onNext, onBack }: { onNext: () => void; onBack: () => void }) {
  const { t } = useTranslation();
  const steps = [
    {
      icon: Upload,
      title: t('onboarding.workflowUploadTitle', '1. Upload Screenplay'),
      description: t(
        'onboarding.workflowUploadDescription',
        'Import your Fountain (.fountain) or Final Draft (.fdx) screenplay file.'
      ),
    },
    {
      icon: Sparkles,
      title: t('onboarding.workflowAnalysisTitle', '2. AI Analysis'),
      description: t(
        'onboarding.workflowAnalysisDescription',
        'Our AI extracts characters, scenes, and dialogue from your screenplay.'
      ),
    },
    {
      icon: Users,
      title: t('onboarding.workflowCharactersTitle', '3. Define Characters'),
      description: t(
        'onboarding.workflowCharactersDescription',
        'Describe appearances, upload references, and assign voices to characters.'
      ),
    },
    {
      icon: Clapperboard,
      title: t('onboarding.workflowShotsTitle', '4. Plan Shots'),
      description: t(
        'onboarding.workflowShotsDescription',
        'Review AI-generated shot breakdowns and customize camera compositions.'
      ),
    },
    {
      icon: Video,
      title: t('onboarding.workflowGenerateTitle', '5. Generate'),
      description: t(
        'onboarding.workflowGenerateDescription',
        'Generate video clips for each shot using state-of-the-art AI models.'
      ),
    },
    {
      icon: Film,
      title: t('onboarding.workflowExportTitle', '6. Export'),
      description: t(
        'onboarding.workflowExportDescription',
        'Assemble your final video and export in your preferred format.'
      ),
    },
  ];

  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <div className="w-16 h-16 bg-brand-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
          <Sparkles className="w-8 h-8 text-brand-400" />
        </div>
        <h2 className="text-2xl font-bold mb-2">
          {t('onboarding.workflowTitle', 'How SceneMachine Works')}
        </h2>
        <p className="text-surface-400">
          {t(
            'onboarding.workflowDescription',
            'Follow this workflow to transform your screenplay into video.'
          )}
        </p>
      </div>

      {/* Workflow steps */}
      <div className="grid grid-cols-2 gap-4 mb-8">
        {steps.map((step, index) => (
          <div
            key={index}
            className="p-4 bg-surface-800/50 rounded-lg border border-surface-700 hover:border-surface-600 transition-colors"
          >
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 bg-brand-500/20 rounded-lg flex items-center justify-center flex-shrink-0">
                <step.icon className="w-5 h-5 text-brand-400" />
              </div>
              <div>
                <h4 className="font-medium mb-1">{step.title}</h4>
                <p className="text-sm text-surface-400">{step.description}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="px-4 py-2 text-surface-400 hover:text-surface-200 flex items-center gap-2"
        >
          <ArrowLeft className="w-5 h-5" />
          {t('onboarding.back', 'Back')}
        </button>
        <button
          onClick={onNext}
          className="px-6 py-3 bg-brand-500 hover:bg-brand-600 rounded-lg font-medium flex items-center gap-2"
        >
          {t('onboarding.continue', 'Continue')}
          <ArrowRight className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}

// Ready step
function ReadyStep({ onComplete, onBack }: { onComplete: () => void; onBack: () => void }) {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const handleCreateProject = () => {
    onComplete();
    // Navigate and trigger project creation modal
    navigate('/?newProject=true');
  };

  const handleExplore = () => {
    onComplete();
    navigate('/');
  };

  return (
    <div className="text-center max-w-lg mx-auto">
      <div className="w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
        <Check className="w-10 h-10 text-green-400" />
      </div>

      <h2 className="text-2xl font-bold mb-4">{t('onboarding.readyTitle', "You're All Set!")}</h2>

      <p className="text-surface-300 mb-8">
        {t(
          'onboarding.readyDescription',
          'SceneMachine is ready to use. Start by creating your first project or explore the application.'
        )}
      </p>

      <div className="space-y-3">
        <button
          onClick={handleCreateProject}
          className="w-full px-6 py-4 bg-brand-500 hover:bg-brand-600 rounded-lg font-medium flex items-center justify-center gap-2"
        >
          <Film className="w-5 h-5" />
          {t('onboarding.createFirstProject', 'Create First Project')}
        </button>

        <button
          onClick={handleExplore}
          className="w-full px-6 py-4 bg-surface-700 hover:bg-surface-600 rounded-lg font-medium"
        >
          {t('onboarding.exploreApplication', 'Explore Application')}
        </button>
      </div>

      <button onClick={onBack} className="mt-6 text-sm text-surface-400 hover:text-surface-200">
        {t('onboarding.goBack', 'Go back')}
      </button>
    </div>
  );
}

export function Onboarding({ onComplete, onSkip }: OnboardingProps) {
  const { t } = useTranslation();
  const [currentStep, setCurrentStep] = useState(0);
  const totalSteps = 4;
  const stepTitles = [
    t('onboarding.stepWelcome', 'Welcome'),
    t('onboarding.stepApiKeys', 'API Keys'),
    t('onboarding.stepWorkflow', 'Workflow'),
    t('onboarding.stepReady', 'Ready'),
  ];

  const handleNext = () => {
    if (currentStep < totalSteps - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-surface-950 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-surface-800">
        <div className="flex items-center gap-2">
          <Film className="w-6 h-6 text-brand-500" />
          <span className="font-semibold">SceneMachine</span>
        </div>
        {onSkip && (
          <button
            onClick={onSkip}
            className="text-sm text-surface-400 hover:text-surface-200 flex items-center gap-1"
          >
            {t('onboarding.skipSetup', 'Skip setup')}
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Progress */}
      <div className="py-6 px-8 border-b border-surface-800">
        <StepIndicator currentStep={currentStep} totalSteps={totalSteps} stepTitles={stepTitles} />
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-8">
        {currentStep === 0 && <WelcomeStep onNext={handleNext} />}
        {currentStep === 1 && <ApiKeysStep onNext={handleNext} onBack={handleBack} />}
        {currentStep === 2 && <WorkflowStep onNext={handleNext} onBack={handleBack} />}
        {currentStep === 3 && <ReadyStep onComplete={onComplete} onBack={handleBack} />}
      </div>
    </div>
  );
}

// Hook to check if onboarding should be shown
export function useOnboardingStatus() {
  const [shouldShowOnboarding, setShouldShowOnboarding] = useState(false);
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    const checkOnboarding = async () => {
      try {
        // Check local storage first
        const completed = localStorage.getItem('scenemachine-onboarding-completed');
        if (completed === 'true') {
          setShouldShowOnboarding(false);
          setIsChecking(false);
          return;
        }

        // Check if user has any settings configured (returning user)
        const settings = await window.electronAPI.backendRequest<any>('settings.get', {});
        const hasApiKeys =
          settings?.apiKeys?.anthropic?.configured || settings?.apiKeys?.openai?.configured;

        // Show onboarding only for truly new users
        setShouldShowOnboarding(!hasApiKeys);
        setIsChecking(false);
      } catch (error) {
        // On error, don't show onboarding
        setShouldShowOnboarding(false);
        setIsChecking(false);
      }
    };

    checkOnboarding();
  }, []);

  const completeOnboarding = () => {
    localStorage.setItem('scenemachine-onboarding-completed', 'true');
    setShouldShowOnboarding(false);
  };

  const skipOnboarding = () => {
    localStorage.setItem('scenemachine-onboarding-completed', 'true');
    setShouldShowOnboarding(false);
  };

  return {
    shouldShowOnboarding,
    isChecking,
    completeOnboarding,
    skipOnboarding,
  };
}
