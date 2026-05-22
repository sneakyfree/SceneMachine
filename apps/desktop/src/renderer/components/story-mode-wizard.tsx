/**
 * Story Mode Wizard Component
 *
 * A simplified, linear flow for Story Mode users.
 * Guides users through the 5-step movie creation process.
 */

import { useState, useCallback } from 'react';
import {
  Upload,
  Users,
  Clapperboard,
  Video,
  Download,
  ArrowRight,
  ArrowLeft,
  Check,
  Loader2,
  Sparkles,
  Play,
  X,
  ChevronDown,
  Film,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useExperienceMode } from '../stores/experience-store';

// Wizard step definition
interface WizardStep {
  id: string;
  title: string;
  subtitle: string;
  description: string;
  icon: typeof Upload;
  color: string;
}

const WIZARD_STEPS: WizardStep[] = [
  {
    id: 'upload',
    title: 'Upload Your Script',
    subtitle: 'Step 1 of 5',
    description:
      'Drag and drop your screenplay file here. I can read Fountain, Final Draft, PDF, or plain text.',
    icon: Upload,
    color: 'blue',
  },
  {
    id: 'characters',
    title: 'Meet Your Characters',
    subtitle: 'Step 2 of 5',
    description:
      "I found the characters in your script. Let's describe how they look so they're consistent throughout your movie.",
    icon: Users,
    color: 'green',
  },
  {
    id: 'scenes',
    title: 'Plan Your Scenes',
    subtitle: 'Step 3 of 5',
    description:
      "I've broken down each scene into camera shots. Review and approve them, or let me adjust anything.",
    icon: Clapperboard,
    color: 'yellow',
  },
  {
    id: 'generate',
    title: 'Create Your Movie',
    subtitle: 'Step 4 of 5',
    description:
      "Now the magic happens! I'm generating video for each shot. You can preview them as they complete.",
    icon: Video,
    color: 'purple',
  },
  {
    id: 'export',
    title: 'Download & Share',
    subtitle: 'Step 5 of 5',
    description:
      'Your movie is ready! Choose your format and quality, then download or share it with the world.',
    icon: Download,
    color: 'brand',
  },
];

interface StoryModeWizardProps {
  projectId: string;
  currentStep: number;
  onStepChange?: (step: number) => void;
  onExit?: () => void;
  // Data for each step
  screenplayUploaded?: boolean;
  characterCount?: number;
  sceneCount?: number;
  generationProgress?: number;
  exportReady?: boolean;
}

// Step indicator with connecting lines
function WizardStepIndicator({
  steps,
  currentStep,
  completedSteps,
}: {
  steps: WizardStep[];
  currentStep: number;
  completedSteps: Set<number>;
}) {
  return (
    <div className="flex items-center justify-center gap-0 w-full max-w-2xl mx-auto mb-8">
      {steps.map((step, index) => {
        const isCompleted = completedSteps.has(index);
        const isCurrent = index === currentStep;
        const isUpcoming = index > currentStep && !isCompleted;
        const Icon = step.icon;

        return (
          <div key={step.id} className="flex items-center">
            {/* Step circle */}
            <div
              className={cn(
                'relative flex items-center justify-center w-12 h-12 rounded-full transition-all',
                isCompleted && 'bg-green-500',
                isCurrent && 'bg-brand-500 ring-4 ring-brand-500/30',
                isUpcoming && 'bg-surface-800 border-2 border-surface-700'
              )}
            >
              {isCompleted ? (
                <Check className="w-6 h-6 text-white" />
              ) : (
                <Icon className={cn('w-6 h-6', isCurrent ? 'text-white' : 'text-surface-500')} />
              )}

              {/* Step number badge */}
              {!isCompleted && (
                <span
                  className={cn(
                    'absolute -bottom-1 -right-1 w-5 h-5 rounded-full text-xs flex items-center justify-center font-medium',
                    isCurrent ? 'bg-white text-brand-600' : 'bg-surface-700 text-surface-400'
                  )}
                >
                  {index + 1}
                </span>
              )}
            </div>

            {/* Connecting line */}
            {index < steps.length - 1 && (
              <div
                className={cn(
                  'w-8 sm:w-12 md:w-16 h-1 mx-1',
                  index < currentStep ? 'bg-green-500' : 'bg-surface-800'
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

// Individual step content components
function UploadStep({ onNext }: { onNext: () => void }) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      setIsUploading(true);

      // Simulate upload (would actually trigger screenplay upload)
      setTimeout(() => {
        setIsUploading(false);
        onNext();
      }, 2000);
    },
    [onNext]
  );

  return (
    <div className="text-center">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={cn(
          'border-2 border-dashed rounded-2xl p-12 transition-all cursor-pointer',
          isDragging
            ? 'border-brand-500 bg-brand-500/10'
            : 'border-surface-700 hover:border-surface-600 bg-surface-800/50'
        )}
      >
        {isUploading ? (
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="w-12 h-12 text-brand-400 animate-spin" />
            <p className="text-lg">Reading your screenplay...</p>
          </div>
        ) : (
          <>
            <Upload
              className={cn(
                'w-12 h-12 mx-auto mb-4',
                isDragging ? 'text-brand-400' : 'text-surface-400'
              )}
            />
            <p className="text-lg font-medium mb-2">
              {isDragging ? 'Drop it here!' : 'Drag & Drop Your Screenplay'}
            </p>
            <p className="text-sm text-surface-400">Or click to browse your files</p>
            <p className="text-xs text-surface-500 mt-4">Supports: .fountain, .fdx, .pdf, .txt</p>
          </>
        )}
      </div>

      <div className="mt-8 p-4 bg-surface-800/50 rounded-lg text-left">
        <h4 className="font-medium mb-2 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-brand-400" />
          What happens next?
        </h4>
        <p className="text-sm text-surface-400">
          Once you upload your script, I'll automatically find all your characters, identify each
          scene, and extract the dialogue. It only takes a few seconds!
        </p>
      </div>
    </div>
  );
}

function CharactersStep({
  characterCount,
  onNext,
  onBack,
}: {
  characterCount: number;
  onNext: () => void;
  onBack: () => void;
}) {
  const [isProcessing, setIsProcessing] = useState(false);

  const handleAutoDescribe = () => {
    setIsProcessing(true);
    // Simulate AI description generation
    setTimeout(() => {
      setIsProcessing(false);
    }, 3000);
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-green-500/20 text-green-400 rounded-full mb-4">
          <Check className="w-4 h-4" />
          Found {characterCount} characters in your screenplay
        </div>
      </div>

      {/* Character cards placeholder */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 max-h-64 overflow-y-auto p-1">
        {Array.from({ length: characterCount }, (_, i) => (
          <div key={i} className="p-4 bg-surface-800 rounded-lg border border-surface-700">
            <div className="w-12 h-12 bg-surface-700 rounded-full mx-auto mb-3" />
            <p className="font-medium text-center text-sm">Character {i + 1}</p>
            <p className="text-xs text-surface-500 text-center">Needs description</p>
          </div>
        ))}
      </div>

      <div className="flex flex-col items-center gap-4">
        <button
          onClick={handleAutoDescribe}
          disabled={isProcessing}
          className="px-6 py-3 bg-brand-500 hover:bg-brand-600 rounded-lg font-medium flex items-center gap-2 disabled:opacity-50"
        >
          {isProcessing ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              AI is describing characters...
            </>
          ) : (
            <>
              <Sparkles className="w-5 h-5" />
              Let AI Describe All Characters
            </>
          )}
        </button>

        <p className="text-sm text-surface-400">
          Or click each character to describe them manually
        </p>
      </div>

      <div className="flex justify-between pt-4">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-surface-400 hover:text-surface-200"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>
        <button
          onClick={onNext}
          className="px-6 py-2 bg-surface-700 hover:bg-surface-600 rounded-lg flex items-center gap-2"
        >
          Continue
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

function ScenesStep({
  sceneCount,
  onNext,
  onBack,
}: {
  sceneCount: number;
  onNext: () => void;
  onBack: () => void;
}) {
  const [approvedCount, setApprovedCount] = useState(0);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const handleAnalyzeAll = () => {
    setIsAnalyzing(true);
    // Simulate analysis
    let count = 0;
    const interval = setInterval(() => {
      count++;
      setApprovedCount(count);
      if (count >= sceneCount) {
        clearInterval(interval);
        setIsAnalyzing(false);
      }
    }, 500);
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500/20 text-blue-400 rounded-full mb-4">
          <Clapperboard className="w-4 h-4" />
          {sceneCount} scenes ready to plan
        </div>
      </div>

      {/* Progress indicator */}
      <div className="p-6 bg-surface-800 rounded-xl">
        <div className="flex justify-between text-sm mb-2">
          <span>Shot planning progress</span>
          <span className="text-brand-400">
            {approvedCount}/{sceneCount} scenes
          </span>
        </div>
        <div className="h-3 bg-surface-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-brand-500 rounded-full transition-all"
            style={{ width: `${(approvedCount / sceneCount) * 100}%` }}
          />
        </div>
      </div>

      <div className="flex flex-col items-center gap-4">
        <button
          onClick={handleAnalyzeAll}
          disabled={isAnalyzing || approvedCount === sceneCount}
          className="px-6 py-3 bg-brand-500 hover:bg-brand-600 rounded-lg font-medium flex items-center gap-2 disabled:opacity-50"
        >
          {isAnalyzing ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Planning shots for scene {approvedCount + 1}...
            </>
          ) : approvedCount === sceneCount ? (
            <>
              <Check className="w-5 h-5" />
              All scenes planned!
            </>
          ) : (
            <>
              <Sparkles className="w-5 h-5" />
              Auto-Plan All Scenes
            </>
          )}
        </button>
      </div>

      <div className="flex justify-between pt-4">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-surface-400 hover:text-surface-200"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>
        <button
          onClick={onNext}
          disabled={approvedCount < sceneCount}
          className="px-6 py-2 bg-surface-700 hover:bg-surface-600 rounded-lg flex items-center gap-2 disabled:opacity-50"
        >
          Continue
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

function GenerateStep({
  progress,
  onNext,
  onBack,
}: {
  progress: number;
  onNext: () => void;
  onBack: () => void;
}) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentProgress, setCurrentProgress] = useState(progress);

  const handleGenerate = () => {
    setIsGenerating(true);
    // Simulate generation progress
    let prog = currentProgress;
    const interval = setInterval(() => {
      prog += 5;
      setCurrentProgress(Math.min(prog, 100));
      if (prog >= 100) {
        clearInterval(interval);
        setIsGenerating(false);
      }
    }, 500);
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-purple-500/20 text-purple-400 rounded-full mb-4">
          <Video className="w-4 h-4" />
          {currentProgress === 100 ? 'Generation complete!' : 'Ready to generate'}
        </div>
      </div>

      {/* Big progress display */}
      <div className="p-8 bg-surface-800 rounded-xl text-center">
        <div className="text-6xl font-bold text-brand-400 mb-4">{currentProgress}%</div>
        <div className="h-4 bg-surface-700 rounded-full overflow-hidden max-w-md mx-auto">
          <div
            className="h-full bg-gradient-to-r from-brand-500 to-purple-500 rounded-full transition-all"
            style={{ width: `${currentProgress}%` }}
          />
        </div>
        {isGenerating && (
          <p className="text-sm text-surface-400 mt-4">
            Creating video clips... This might take a few minutes.
          </p>
        )}
      </div>

      {/* Preview grid */}
      {currentProgress > 0 && (
        <div className="grid grid-cols-4 gap-2">
          {Array.from({ length: Math.floor(currentProgress / 10) }, (_, i) => (
            <div
              key={i}
              className="aspect-video bg-surface-700 rounded-lg flex items-center justify-center"
            >
              <Play className="w-6 h-6 text-surface-500" />
            </div>
          ))}
        </div>
      )}

      <div className="flex justify-center">
        {currentProgress < 100 ? (
          <button
            onClick={handleGenerate}
            disabled={isGenerating}
            className="px-8 py-4 bg-gradient-to-r from-brand-500 to-purple-500 hover:from-brand-600 hover:to-purple-600 rounded-xl font-medium text-lg flex items-center gap-3 disabled:opacity-50"
          >
            {isGenerating ? (
              <>
                <Loader2 className="w-6 h-6 animate-spin" />
                Creating Your Movie...
              </>
            ) : (
              <>
                <Sparkles className="w-6 h-6" />
                Make My Movie
              </>
            )}
          </button>
        ) : (
          <button
            onClick={onNext}
            className="px-8 py-4 bg-green-500 hover:bg-green-600 rounded-xl font-medium text-lg flex items-center gap-3"
          >
            <Check className="w-6 h-6" />
            Continue to Export
            <ArrowRight className="w-5 h-5" />
          </button>
        )}
      </div>
    </div>
  );
}

function ExportStep({ onBack }: { onBack: () => void }) {
  const [isExporting, setIsExporting] = useState(false);
  const [exportComplete, setExportComplete] = useState(false);

  const handleExport = () => {
    setIsExporting(true);
    setTimeout(() => {
      setIsExporting(false);
      setExportComplete(true);
    }, 3000);
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        {exportComplete ? (
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-green-500/20 text-green-400 rounded-full mb-4">
            <Check className="w-4 h-4" />
            Your movie is ready!
          </div>
        ) : (
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-brand-500/20 text-brand-400 rounded-full mb-4">
            <Download className="w-4 h-4" />
            Choose your export settings
          </div>
        )}
      </div>

      {exportComplete ? (
        <div className="p-8 bg-surface-800 rounded-xl text-center">
          <div className="w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
            <Film className="w-10 h-10 text-green-400" />
          </div>
          <h3 className="text-2xl font-bold mb-2">Congratulations!</h3>
          <p className="text-surface-400 mb-6">Your movie has been exported successfully.</p>
          <div className="flex justify-center gap-4">
            <button className="px-6 py-3 bg-brand-500 hover:bg-brand-600 rounded-lg font-medium flex items-center gap-2">
              <Play className="w-5 h-5" />
              Watch Movie
            </button>
            <button className="px-6 py-3 bg-surface-700 hover:bg-surface-600 rounded-lg flex items-center gap-2">
              <Download className="w-5 h-5" />
              Open Folder
            </button>
          </div>
        </div>
      ) : (
        <>
          {/* Quality options */}
          <div className="grid grid-cols-2 gap-4">
            <button className="p-4 bg-surface-800 hover:bg-surface-700 rounded-xl border-2 border-brand-500 text-left">
              <p className="font-medium mb-1">Great Quality</p>
              <p className="text-sm text-surface-400">1080p - Perfect for sharing online</p>
            </button>
            <button className="p-4 bg-surface-800 hover:bg-surface-700 rounded-xl border-2 border-surface-700 text-left">
              <p className="font-medium mb-1">Best Quality</p>
              <p className="text-sm text-surface-400">4K - For big screens</p>
            </button>
          </div>

          <div className="flex justify-center">
            <button
              onClick={handleExport}
              disabled={isExporting}
              className="px-8 py-4 bg-brand-500 hover:bg-brand-600 rounded-xl font-medium text-lg flex items-center gap-3 disabled:opacity-50"
            >
              {isExporting ? (
                <>
                  <Loader2 className="w-6 h-6 animate-spin" />
                  Exporting...
                </>
              ) : (
                <>
                  <Download className="w-6 h-6" />
                  Export My Movie
                </>
              )}
            </button>
          </div>
        </>
      )}

      <div className="flex justify-start pt-4">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-surface-400 hover:text-surface-200"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>
      </div>
    </div>
  );
}

export function StoryModeWizard({
  projectId,
  currentStep = 0,
  onStepChange,
  onExit,
  screenplayUploaded = false,
  characterCount = 6,
  sceneCount = 12,
  generationProgress = 0,
  exportReady = false,
}: StoryModeWizardProps) {
  const [step, setStep] = useState(currentStep);
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  const { isStory } = useExperienceMode();

  // Don't show wizard if not in story mode
  if (!isStory) return null;

  const handleNext = () => {
    setCompletedSteps((prev) => new Set([...prev, step]));
    const nextStep = step + 1;
    setStep(nextStep);
    onStepChange?.(nextStep);
  };

  const handleBack = () => {
    const prevStep = step - 1;
    setStep(prevStep);
    onStepChange?.(prevStep);
  };

  const currentStepData = WIZARD_STEPS[step];

  return (
    <div className="min-h-screen bg-surface-950 p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <Film className="w-8 h-8 text-brand-500" />
          <span className="font-semibold text-lg">SceneMachine</span>
        </div>
        {onExit && (
          <button
            onClick={onExit}
            className="flex items-center gap-2 text-surface-400 hover:text-surface-200"
          >
            Exit Story Mode
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Step indicator */}
      <WizardStepIndicator
        steps={WIZARD_STEPS}
        currentStep={step}
        completedSteps={completedSteps}
      />

      {/* Current step content */}
      <div className="max-w-2xl mx-auto">
        <div className="text-center mb-8">
          <p className="text-sm text-brand-400 mb-2">{currentStepData.subtitle}</p>
          <h1 className="text-3xl font-bold mb-3">{currentStepData.title}</h1>
          <p className="text-surface-400">{currentStepData.description}</p>
        </div>

        {/* Step-specific content */}
        {step === 0 && <UploadStep onNext={handleNext} />}
        {step === 1 && (
          <CharactersStep characterCount={characterCount} onNext={handleNext} onBack={handleBack} />
        )}
        {step === 2 && (
          <ScenesStep sceneCount={sceneCount} onNext={handleNext} onBack={handleBack} />
        )}
        {step === 3 && (
          <GenerateStep progress={generationProgress} onNext={handleNext} onBack={handleBack} />
        )}
        {step === 4 && <ExportStep onBack={handleBack} />}
      </div>
    </div>
  );
}
