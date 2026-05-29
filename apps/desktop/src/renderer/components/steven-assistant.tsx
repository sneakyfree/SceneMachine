/**
 * Steven AI Assistant Component
 *
 * An ever-present AI companion that guides users through the movie-making process.
 * Named after Steven Spielberg - the most universally recognized director.
 */

import { useState, useEffect, useRef } from 'react';
import {
  MessageCircle,
  X,
  Minimize2,
  Maximize2,
  Send,
  Sparkles,
  Film,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  Lightbulb,
  CheckCircle2,
  AlertCircle,
  PartyPopper,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useExperienceStore, STEVEN_MESSAGES, useExperienceMode } from '../stores/experience-store';
import { useLocation } from 'react-router-dom';
import { useTranslation } from '../i18n/use-translation';

interface StevenMessage {
  id: string;
  content: string;
  type: 'info' | 'success' | 'warning' | 'celebration' | 'user';
  timestamp: number;
}

// Context-aware suggestions based on current page.
// Stored as i18n key + English fallback so the component can resolve at render.
interface Suggestion {
  key: string;
  en: string;
}

const PAGE_SUGGESTIONS: Record<string, Suggestion[]> = {
  '/': [
    { key: 'steven.suggestStartNewProject', en: 'How do I start a new project?' },
    { key: 'steven.suggestFileFormats', en: 'What file formats can I upload?' },
    { key: 'steven.suggestHowItWorks', en: 'Show me how SceneMachine works' },
  ],
  '/project': [
    { key: 'steven.suggestWhatNext', en: 'What should I do next?' },
    { key: 'steven.suggestUploadScreenplay', en: 'How do I upload my screenplay?' },
    { key: 'steven.suggestAboutWorkflow', en: 'Tell me about the workflow' },
  ],
  '/character-lab': [
    { key: 'steven.suggestDescribeCharacter', en: 'How do I describe a character?' },
    { key: 'steven.suggestReferenceImages', en: 'What are reference images for?' },
    { key: 'steven.suggestAssignVoices', en: 'How do I assign voices?' },
  ],
  '/scene-planning': [
    { key: 'steven.suggestShotBreakdown', en: 'What is a shot breakdown?' },
    { key: 'steven.suggestCustomizeCameraAngles', en: 'How do I customize camera angles?' },
    { key: 'steven.suggestShotTypes', en: 'What shot types are available?' },
  ],
  '/generation': [
    { key: 'steven.suggestGenerationTime', en: 'How long does generation take?' },
    { key: 'steven.suggestDislikeResult', en: "What if I don't like a result?" },
    { key: 'steven.suggestPrioritizeShots', en: 'How do I prioritize certain shots?' },
  ],
  '/timeline': [
    { key: 'steven.suggestReorderClips', en: 'How do I reorder clips?' },
    { key: 'steven.suggestTransitions', en: 'What are transitions?' },
    { key: 'steven.suggestTrimClip', en: 'How do I trim a clip?' },
  ],
  '/export': [
    { key: 'steven.suggestChooseFormat', en: 'What format should I choose?' },
    { key: 'steven.suggestBestResolution', en: 'What resolution is best?' },
    { key: 'steven.suggestAddWatermark', en: 'How do I add a watermark?' },
  ],
};

// Steven's avatar component
function StevenAvatar({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const sizeClasses = {
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-12 h-12',
  };

  return (
    <div
      className={cn(
        'rounded-full bg-gradient-to-br from-brand-500 to-brand-600 flex items-center justify-center shadow-lg',
        sizeClasses[size]
      )}
    >
      <Film
        className={cn(
          'text-white',
          size === 'sm' ? 'w-4 h-4' : size === 'md' ? 'w-5 h-5' : 'w-6 h-6'
        )}
      />
    </div>
  );
}

// Message bubble component
function MessageBubble({ message }: { message: StevenMessage }) {
  const isUser = message.type === 'user';

  const typeIcons = {
    info: <Lightbulb className="w-4 h-4 text-blue-400" />,
    success: <CheckCircle2 className="w-4 h-4 text-green-400" />,
    warning: <AlertCircle className="w-4 h-4 text-yellow-400" />,
    celebration: <PartyPopper className="w-4 h-4 text-purple-400" />,
    user: null,
  };

  return (
    <div className={cn('flex gap-2', isUser && 'flex-row-reverse')}>
      {!isUser && <StevenAvatar size="sm" />}
      <div
        className={cn(
          'max-w-[85%] rounded-2xl px-4 py-2',
          isUser
            ? 'bg-brand-500 text-white rounded-br-sm'
            : 'bg-surface-800 text-surface-100 rounded-bl-sm'
        )}
      >
        {!isUser && message.type !== 'info' && (
          <div className="flex items-center gap-1 mb-1">{typeIcons[message.type]}</div>
        )}
        <p className="text-sm leading-relaxed">{message.content}</p>
      </div>
    </div>
  );
}

// Quick suggestion button
function SuggestionButton({ suggestion, onClick }: { suggestion: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="px-3 py-1.5 bg-surface-800 hover:bg-surface-700 rounded-full text-xs text-surface-300 hover:text-surface-100 transition-colors text-left"
    >
      {suggestion}
    </button>
  );
}

export function StevenAssistant() {
  const { t } = useTranslation();
  const location = useLocation();
  const { mode } = useExperienceMode();
  const {
    stevenEnabled,
    stevenMinimized,
    setStevenMinimized,
    stevenMessageHistory,
    sendStevenMessage,
  } = useExperienceStore();

  const [isExpanded, setIsExpanded] = useState(false);
  const [messages, setMessages] = useState<StevenMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Get suggestions based on current page
  const currentSuggestions = PAGE_SUGGESTIONS[location.pathname] || PAGE_SUGGESTIONS['/'];

  // Initialize with welcome message
  useEffect(() => {
    if (messages.length === 0) {
      const welcomeMessage = STEVEN_MESSAGES.welcome[0];
      setMessages([
        {
          id: '1',
          content: welcomeMessage,
          type: 'info',
          timestamp: Date.now(),
        },
      ]);
    }
  }, []);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input when expanded
  useEffect(() => {
    if (isExpanded) {
      inputRef.current?.focus();
    }
  }, [isExpanded]);

  // Handle user message
  const handleSend = async () => {
    if (!inputValue.trim()) return;

    const userMessage: StevenMessage = {
      id: Date.now().toString(),
      content: inputValue,
      type: 'user',
      timestamp: Date.now(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsThinking(true);

    // Simulate AI response (in production, this would call an LLM)
    setTimeout(() => {
      const response = generateResponse(inputValue, location.pathname, t);
      const responseMessage: StevenMessage = {
        id: (Date.now() + 1).toString(),
        content: response.content,
        type: response.type,
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, responseMessage]);
      setIsThinking(false);
    }, 1000);
  };

  // Handle suggestion click
  const handleSuggestion = (suggestion: string) => {
    setInputValue(suggestion);
    handleSend();
  };

  // Don't render if Steven is disabled
  if (!stevenEnabled) return null;

  // Minimized state - just show floating button
  if (stevenMinimized) {
    return (
      <button
        onClick={() => setStevenMinimized(false)}
        className="fixed bottom-6 right-6 z-50 p-3 bg-brand-500 hover:bg-brand-600 rounded-full shadow-lg hover:shadow-xl transition-all group"
        title={t('steven.openAssistant', 'Open Steven Assistant')}
      >
        <MessageCircle className="w-6 h-6 text-white" />
        <span className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-surface-950" />
      </button>
    );
  }

  return (
    <div
      className={cn(
        'fixed bottom-6 right-6 z-50 flex flex-col bg-surface-900 rounded-2xl shadow-2xl border border-surface-800 transition-all duration-300',
        isExpanded ? 'w-96 h-[500px]' : 'w-80 h-auto'
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-surface-800">
        <div className="flex items-center gap-3">
          <StevenAvatar size="sm" />
          <div>
            <h3 className="font-medium text-sm">Steven</h3>
            <p className="text-xs text-surface-400">
              {t('steven.directorsAssistant', "Your Director's Assistant")}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="icon-btn p-2 text-surface-400 hover:text-surface-200 transition-colors rounded"
            title={isExpanded ? t('steven.collapse', 'Collapse') : t('steven.expand', 'Expand')}
            aria-label={
              isExpanded
                ? t('steven.collapseAssistant', 'Collapse Steven assistant')
                : t('steven.expandAssistant', 'Expand Steven assistant')
            }
          >
            {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
          </button>
          <button
            onClick={() => setStevenMinimized(true)}
            className="icon-btn p-2 text-surface-400 hover:text-surface-200 transition-colors rounded"
            title={t('steven.minimize', 'Minimize')}
            aria-label={t('steven.minimizeAssistant', 'Minimize Steven assistant')}
          >
            <Minimize2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className={cn('flex-1 overflow-y-auto p-4 space-y-4', !isExpanded && 'max-h-64')}>
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isThinking && (
          <div className="flex gap-2">
            <StevenAvatar size="sm" />
            <div className="bg-surface-800 rounded-2xl rounded-bl-sm px-4 py-2">
              <div className="flex gap-1">
                <span
                  className="w-2 h-2 bg-surface-500 rounded-full animate-bounce"
                  style={{ animationDelay: '0ms' }}
                />
                <span
                  className="w-2 h-2 bg-surface-500 rounded-full animate-bounce"
                  style={{ animationDelay: '150ms' }}
                />
                <span
                  className="w-2 h-2 bg-surface-500 rounded-full animate-bounce"
                  style={{ animationDelay: '300ms' }}
                />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggestions */}
      {isExpanded && messages.length <= 2 && (
        <div className="px-4 py-2 border-t border-surface-800">
          <p className="text-xs text-surface-500 mb-2">
            {t('steven.quickQuestions', 'Quick questions:')}
          </p>
          <div className="flex flex-wrap gap-2">
            {currentSuggestions.map((suggestion) => {
              const label = t(suggestion.key, suggestion.en);
              return (
                <SuggestionButton
                  key={suggestion.key}
                  suggestion={label}
                  onClick={() => handleSuggestion(label)}
                />
              );
            })}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="p-3 border-t border-surface-800">
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder={t('steven.askAnything', 'Ask Steven anything...')}
            className="flex-1 bg-surface-800 border-none rounded-full px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          <button
            onClick={handleSend}
            disabled={!inputValue.trim() || isThinking}
            className="p-2 bg-brand-500 hover:bg-brand-600 disabled:opacity-50 disabled:hover:bg-brand-500 rounded-full transition-colors"
          >
            <Send className="w-4 h-4 text-white" />
          </button>
        </div>
      </div>
    </div>
  );
}

// Generate contextual responses (placeholder - would use LLM in production)
function generateResponse(
  question: string,
  currentPath: string,
  t: (key: string, fallback: string) => string
): { content: string; type: 'info' | 'success' | 'warning' | 'celebration' } {
  const q = question.toLowerCase();

  // Project creation
  if (q.includes('start') || q.includes('new project') || q.includes('begin')) {
    return {
      content: t(
        'steven.responseStartProject',
        'To start a new project, click the "+ New Project" button on the home page. Give your project a name, then drag and drop your screenplay file to get started!'
      ),
      type: 'info',
    };
  }

  // File formats
  if (q.includes('format') || q.includes('file') || q.includes('upload')) {
    return {
      content: t(
        'steven.responseFileFormats',
        'I can read Fountain (.fountain), Final Draft (.fdx), PDF (.pdf), and plain text (.txt) files. Fountain and Final Draft work best because they have proper screenplay formatting.'
      ),
      type: 'info',
    };
  }

  // Workflow
  if (q.includes('workflow') || (q.includes('how') && q.includes('work'))) {
    return {
      content: t(
        'steven.responseWorkflow',
        "Here's how we'll make your movie together: 1) Upload your screenplay, 2) I'll analyze it and find your characters, 3) You'll describe how they look, 4) I'll plan camera shots for each scene, 5) We'll generate video clips, 6) Export your finished movie!"
      ),
      type: 'info',
    };
  }

  // Characters
  if (q.includes('character') || q.includes('describe')) {
    return {
      content: t(
        'steven.responseCharacters',
        "For each character, you can describe their appearance (age, height, hair, etc.), upload reference photos, and even assign a voice for dialogue. The more detail you give, the more consistent they'll look across scenes!"
      ),
      type: 'info',
    };
  }

  // Shots
  if (q.includes('shot') || q.includes('camera') || q.includes('angle')) {
    return {
      content: t(
        'steven.responseShots',
        'A shot breakdown is like a comic book version of your scene - each panel shows a different camera angle. I suggest shots like close-ups for emotional moments and wide shots to show the setting. You can customize any of my suggestions!'
      ),
      type: 'info',
    };
  }

  // Generation
  if (q.includes('generate') || q.includes('long') || q.includes('time')) {
    return {
      content: t(
        'steven.responseGeneration',
        "Each shot typically takes 30-60 seconds to generate. A full scene might take 5-10 minutes. I'll keep you updated on progress, and you can preview completed shots while others are still cooking!"
      ),
      type: 'info',
    };
  }

  // Don't like result
  if (q.includes("don't like") || q.includes('change') || q.includes('redo')) {
    return {
      content: t(
        'steven.responseDislike',
        'No problem! If a generated shot doesn\'t look right, just click "Reject" and I\'ll generate a new version. You can also tweak the description to guide the AI toward what you want.'
      ),
      type: 'info',
    };
  }

  // Resolution/format
  if (q.includes('resolution') || q.includes('quality')) {
    return {
      content: t(
        'steven.responseResolution',
        "For sharing online, 1080p (Full HD) is perfect - it looks great and files aren't too big. If you're planning for a big screen or professional use, go for 4K. For quick previews, 720p is fast to export."
      ),
      type: 'info',
    };
  }

  // Next steps
  if (q.includes('next') || q.includes('what should')) {
    if (currentPath === '/') {
      return {
        content: t(
          'steven.responseNextHome',
          'Let\'s create a new project! Click the "+ New Project" button and give it a name. Then we can upload your screenplay.'
        ),
        type: 'info',
      };
    }
    if (currentPath.includes('project')) {
      return {
        content: t(
          'steven.responseNextProject',
          "Looking at your project, the next step is to upload a screenplay. Just drag and drop your file, and I'll take it from there!"
        ),
        type: 'info',
      };
    }
    return {
      content: t(
        'steven.responseNextDefault',
        "Based on where you are, I'd suggest moving to the next step in our workflow. Would you like me to guide you through it?"
      ),
      type: 'info',
    };
  }

  // Default response
  return {
    content: t(
      'steven.responseDefault',
      "Great question! I'm here to help with anything related to making your movie. You can ask me about uploading screenplays, describing characters, planning shots, generating videos, or exporting your final film."
    ),
    type: 'info',
  };
}

// Export for use in other components to trigger Steven messages
export function useStevenAnnounce() {
  const { sendStevenMessage, stevenEnabled } = useExperienceStore();

  return {
    announce: (message: string, type: 'info' | 'success' | 'warning' | 'celebration' = 'info') => {
      if (stevenEnabled) {
        sendStevenMessage(message, type);
      }
    },
    isEnabled: stevenEnabled,
  };
}
