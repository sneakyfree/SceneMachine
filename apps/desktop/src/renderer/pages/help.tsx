/**
 * Help and documentation page.
 * Provides user guides, FAQs, and keyboard shortcuts reference.
 */

import { useState } from 'react';
import {
  HelpCircle,
  Book,
  Keyboard,
  MessageCircle,
  ExternalLink,
  ChevronRight,
  ChevronDown,
  Search,
  Film,
  Users,
  Layers,
  Zap,
  Download,
  Settings,
  PlayCircle,
  FileText,
  Sparkles,
  Video,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { getAllShortcuts, formatShortcut } from '../hooks/use-keyboard-shortcuts';
import { useTranslation } from '../i18n/use-translation';

// Help section interface
interface HelpSection {
  id: string;
  title: string;
  icon: typeof HelpCircle;
  content: React.ReactNode;
}

// FAQ item
interface FAQItem {
  question: string;
  answer: string;
}

// Collapsible FAQ component. Accepts an optional `searchQuery` to live-filter
// items by case-insensitive substring match on question OR answer. Before
// iter 16 the help page captured `searchQuery` state but never used it —
// the search box was decorative (P2 from /qa_screenshot_tour report).
function FAQAccordion({
  items,
  searchQuery = '',
}: {
  items: FAQItem[];
  searchQuery?: string;
}) {
  const { t } = useTranslation();
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  const query = searchQuery.trim().toLowerCase();
  const filtered = query
    ? items.filter(
        (item) =>
          item.question.toLowerCase().includes(query) ||
          item.answer.toLowerCase().includes(query),
      )
    : items;

  if (query && filtered.length === 0) {
    return (
      <div className="text-center py-8 text-surface-400">
        <p>
          {t('help.noFaqMatch', 'No FAQ items match')} {`"${searchQuery}"`}.
        </p>
        <p className="text-sm mt-1">{t('help.tryDifferentSearch', 'Try a different search term.')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {filtered.map((item, index) => (
        <div key={index} className="border border-surface-700 rounded-lg overflow-hidden">
          <button
            onClick={() => setOpenIndex(openIndex === index ? null : index)}
            className="w-full flex items-center justify-between p-4 text-left hover:bg-surface-800 transition-colors"
          >
            <span className="font-medium">{item.question}</span>
            {openIndex === index ? (
              <ChevronDown className="w-5 h-5 text-surface-400" />
            ) : (
              <ChevronRight className="w-5 h-5 text-surface-400" />
            )}
          </button>
          {(openIndex === index || query) && (
            <div className="px-4 pb-4 text-surface-300 text-sm leading-relaxed">{item.answer}</div>
          )}
        </div>
      ))}
    </div>
  );
}

// Keyboard shortcuts section
function KeyboardShortcutsSection() {
  const shortcutGroups = getAllShortcuts();

  return (
    <div className="space-y-6">
      {shortcutGroups.map((group) => (
        <div key={group.category}>
          <h3 className="text-sm font-medium text-surface-400 mb-3">{group.category}</h3>
          <div className="grid gap-2">
            {group.shortcuts.map((shortcut) => (
              <div
                key={shortcut.description}
                className="flex items-center justify-between p-2 bg-surface-800/50 rounded"
              >
                <span className="text-sm">{shortcut.description}</span>
                <kbd className="px-2 py-1 bg-surface-700 rounded text-xs font-mono">
                  {formatShortcut(shortcut)}
                </kbd>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// Quick start guide
function QuickStartGuide() {
  const { t } = useTranslation();
  const steps = [
    {
      icon: FileText,
      title: t('help.quickStartStep1Title', '1. Import Your Screenplay'),
      description: t(
        'help.quickStartStep1Desc',
        'Start by uploading your screenplay in PDF, FDX (Final Draft), or plain text format. SceneMachine will automatically parse scenes, characters, and dialogue.',
      ),
    },
    {
      icon: Users,
      title: t('help.quickStartStep2Title', '2. Design Your Characters'),
      description: t(
        'help.quickStartStep2Desc',
        'Use the Character Lab to define visual appearances for each character. Add reference images, describe their look, and set consistent attributes.',
      ),
    },
    {
      icon: Layers,
      title: t('help.quickStartStep3Title', '3. Plan Your Scenes'),
      description: t(
        'help.quickStartStep3Desc',
        'Review each scene and plan your shots. Choose shot types, camera angles, and composition. SceneMachine suggests shots based on the screenplay.',
      ),
    },
    {
      icon: Zap,
      title: t('help.quickStartStep4Title', '4. Generate Videos'),
      description: t(
        'help.quickStartStep4Desc',
        'Queue your shots for generation. Watch as AI creates video clips based on your screenplay and visual specifications.',
      ),
    },
    {
      icon: Video,
      title: t('help.quickStartStep5Title', '5. Review & Refine'),
      description: t(
        'help.quickStartStep5Desc',
        'Preview generated shots, provide feedback, and regenerate any that need improvement. Approve shots that meet your vision.',
      ),
    },
    {
      icon: Download,
      title: t('help.quickStartStep6Title', '6. Export Your Movie'),
      description: t(
        'help.quickStartStep6Desc',
        'Assemble approved shots into scenes and export your final movie in various formats and quality levels.',
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {steps.map((step) => (
        <div key={step.title} className="flex gap-4">
          <div className="shrink-0">
            <div className="w-10 h-10 rounded-lg bg-brand-500/20 flex items-center justify-center">
              <step.icon className="w-5 h-5 text-brand-400" />
            </div>
          </div>
          <div>
            <h3 className="font-medium mb-1">{step.title}</h3>
            <p className="text-sm text-surface-400">{step.description}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

// Feature guide
function FeatureGuide() {
  const { t } = useTranslation();
  const features = [
    {
      title: t('help.featureScreenplayParsingTitle', 'Screenplay Parsing'),
      description: t(
        'help.featureScreenplayParsingDesc',
        'SceneMachine supports multiple screenplay formats including Final Draft (.fdx), PDF, and plain text. The parser identifies scene headings, action lines, character names, dialogue, and parentheticals.',
      ),
      tips: [
        t('help.featureScreenplayParsingTip1', 'Use standard screenplay formatting for best results'),
        t('help.featureScreenplayParsingTip2', 'Scene headings should follow INT/EXT format'),
        t('help.featureScreenplayParsingTip3', 'Character names should be in CAPS'),
      ],
    },
    {
      title: t('help.featureCharacterLabTitle', 'Character Lab'),
      description: t(
        'help.featureCharacterLabDesc',
        'The Character Lab allows you to define consistent visual appearances for your characters. Upload reference images, describe physical attributes, and set visual style guides.',
      ),
      tips: [
        t('help.featureCharacterLabTip1', 'Add multiple reference images for better consistency'),
        t('help.featureCharacterLabTip2', 'Be specific about age, build, clothing style'),
        t('help.featureCharacterLabTip3', 'Use the visual style field for artistic direction'),
      ],
    },
    {
      title: t('help.featureShotPlanningTitle', 'Shot Planning'),
      description: t(
        'help.featureShotPlanningDesc',
        'Plan your shots with precision using the Scene Planning tools. Choose shot types, camera movements, and composition. Add visual notes and references.',
      ),
      tips: [
        t('help.featureShotPlanningTip1', 'Use the AI suggestions as a starting point'),
        t('help.featureShotPlanningTip2', 'Match shot types to the emotional content'),
        t('help.featureShotPlanningTip3', 'Consider pacing when setting shot durations'),
      ],
    },
    {
      title: t('help.featureVideoGenerationTitle', 'Video Generation'),
      description: t(
        'help.featureVideoGenerationDesc',
        'Queue shots for AI video generation. Monitor progress in real-time and manage your generation queue with priority controls.',
      ),
      tips: [
        t('help.featureVideoGenerationTip1', 'Start with a few test shots to calibrate'),
        t('help.featureVideoGenerationTip2', 'Use the prompt preview to verify descriptions'),
        t('help.featureVideoGenerationTip3', 'Higher priority items are processed first'),
      ],
    },
    {
      title: t('help.featureTimelineEditorTitle', 'Timeline Editor'),
      description: t(
        'help.featureTimelineEditorDesc',
        'Arrange and fine-tune your shots in the interactive timeline. Adjust durations, reorder clips, and preview the assembled sequence.',
      ),
      tips: [
        t('help.featureTimelineEditorTip1', 'Use keyboard shortcuts for faster editing'),
        t('help.featureTimelineEditorTip2', 'Lock clips to prevent accidental changes'),
        t('help.featureTimelineEditorTip3', 'Preview the sequence before exporting'),
      ],
    },
    {
      title: t('help.featureExportOptionsTitle', 'Export Options'),
      description: t(
        'help.featureExportOptionsDesc',
        'Export your final movie in various formats and quality levels. Choose from MP4 (H.264/H.265), ProRes, WebM, and more.',
      ),
      tips: [
        t('help.featureExportOptionsTip1', 'Use Draft quality for quick previews'),
        t('help.featureExportOptionsTip2', 'Master quality for final delivery'),
        t('help.featureExportOptionsTip3', 'H.264 for widest compatibility'),
      ],
    },
  ];

  const [expandedFeature, setExpandedFeature] = useState<string | null>(null);

  return (
    <div className="space-y-4">
      {features.map((feature) => (
        <div key={feature.title} className="border border-surface-700 rounded-lg overflow-hidden">
          <button
            onClick={() =>
              setExpandedFeature(expandedFeature === feature.title ? null : feature.title)
            }
            className="w-full flex items-center justify-between p-4 text-left hover:bg-surface-800 transition-colors"
          >
            <span className="font-medium">{feature.title}</span>
            {expandedFeature === feature.title ? (
              <ChevronDown className="w-5 h-5 text-surface-400" />
            ) : (
              <ChevronRight className="w-5 h-5 text-surface-400" />
            )}
          </button>
          {expandedFeature === feature.title && (
            <div className="px-4 pb-4 space-y-3">
              <p className="text-sm text-surface-300">{feature.description}</p>
              <div>
                <h4 className="text-sm font-medium text-surface-400 mb-2">{t('help.tipsLabel', 'Tips:')}</h4>
                <ul className="space-y-1">
                  {feature.tips.map((tip, i) => (
                    <li key={i} className="text-sm text-surface-400 flex items-start gap-2">
                      <Sparkles className="w-3 h-3 mt-1 text-brand-400 shrink-0" />
                      {tip}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export function HelpPage() {
  const { t } = useTranslation();
  const [activeSection, setActiveSection] = useState('quickstart');
  const [searchQuery, setSearchQuery] = useState('');

  // FAQ data
  const faqItems: FAQItem[] = [
    {
      question: t('help.faqFormatsQuestion', 'What screenplay formats are supported?'),
      answer: t(
        'help.faqFormatsAnswer',
        'SceneMachine supports Final Draft (.fdx), PDF, Fountain (.fountain), and plain text formats. For best results, use properly formatted screenplays following industry standards.',
      ),
    },
    {
      question: t('help.faqGenTimeQuestion', 'How long does video generation take?'),
      answer: t(
        'help.faqGenTimeAnswer',
        'Generation time varies based on the provider, video length, and queue size. Typically, a 3-5 second clip takes 30-60 seconds to generate. You can monitor progress in real-time from the Generation page.',
      ),
    },
    {
      question: t('help.faqApiKeysQuestion', 'Can I use my own API keys?'),
      answer: t(
        'help.faqApiKeysAnswer',
        'Yes! Go to Settings > API Keys to configure your own API keys for various providers including Anthropic, OpenAI, Replicate, Fal.ai, RunwayML, and ElevenLabs.',
      ),
    },
    {
      question: t('help.faqConsistencyQuestion', 'How do I ensure character consistency?'),
      answer: t(
        'help.faqConsistencyAnswer',
        'Use the Character Lab to define detailed visual descriptions and reference images for each character. The AI will use these references to maintain consistency across shots.',
      ),
    },
    {
      question: t('help.faqResolutionsQuestion', 'What video resolutions are available?'),
      answer: t(
        'help.faqResolutionsAnswer',
        'SceneMachine supports 720p, 1080p, 1440p, and 4K resolutions. Higher resolutions may take longer to generate and consume more API credits.',
      ),
    },
    {
      question: t('help.faqRegenerateQuestion', 'Can I regenerate a specific shot?'),
      answer: t(
        'help.faqRegenerateAnswer',
        'Yes! You can regenerate any shot from the Scene Planning or Generation pages. Use the feedback feature to provide guidance for the regeneration.',
      ),
    },
    {
      question: t('help.faqExportQuestion', 'How do I export my final movie?'),
      answer: t(
        'help.faqExportAnswer',
        'Navigate to the Export page from your project. Choose your preferred format, quality level, and resolution. The export process will assemble all approved shots into a single video file.',
      ),
    },
    {
      question: t('help.faqDataSecurityQuestion', 'Is my data stored securely?'),
      answer: t(
        'help.faqDataSecurityAnswer',
        'All project data is stored locally on your machine by default. API keys are encrypted in your system keychain. We recommend regular backups of your project files.',
      ),
    },
    {
      question: t('help.faqBetterResultsQuestion', 'How can I get better generation results?'),
      answer: t(
        'help.faqBetterResultsAnswer',
        'Be specific in your shot descriptions, use reference images in Character Lab, provide clear prompts, and use the feedback system to guide regenerations. Experiment with different providers for varying styles.',
      ),
    },
    {
      question: t('help.faqFailQuestion', 'What if generation fails?'),
      answer: t(
        'help.faqFailAnswer',
        'Failed generations can be retried from the queue. Check the error message for details. Common issues include API limits, network problems, or content policy violations.',
      ),
    },
  ];

  // When the user types anything in the search box, auto-switch to the FAQ
  // section since that's where searchable content lives. Iter 16 wiring —
  // the input state existed since the page shipped but never affected the
  // view.
  const effectiveSection = searchQuery.trim() ? 'faq' : activeSection;

  const sections: HelpSection[] = [
    {
      id: 'quickstart',
      title: t('help.sectionQuickStart', 'Quick Start'),
      icon: PlayCircle,
      content: <QuickStartGuide />,
    },
    {
      id: 'features',
      title: t('help.sectionFeatureGuide', 'Feature Guide'),
      icon: Book,
      content: <FeatureGuide />,
    },
    {
      id: 'shortcuts',
      title: t('help.sectionKeyboardShortcuts', 'Keyboard Shortcuts'),
      icon: Keyboard,
      content: <KeyboardShortcutsSection />,
    },
    {
      id: 'faq',
      title: t('help.sectionFaq', 'FAQ'),
      icon: MessageCircle,
      content: <FAQAccordion items={faqItems} searchQuery={searchQuery} />,
    },
  ];

  const activeContent = sections.find((s) => s.id === effectiveSection);

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-8 max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <HelpCircle className="w-6 h-6 text-brand-400" />
            {t('help.pageTitle', 'Help & Documentation')}
          </h1>
          <p className="text-surface-400 mt-1">
            {t('help.pageSubtitle', 'Learn how to use SceneMachine to create stunning AI-generated movies')}
          </p>
        </div>

        {/* Search */}
        <div className="relative mb-6">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-surface-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t('help.searchPlaceholder', 'Search help topics...')}
            className="w-full pl-10 pr-4 py-3 bg-surface-800 border border-surface-700 rounded-lg focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
          />
        </div>

        {/* Main content */}
        <div className="flex gap-8">
          {/* Sidebar */}
          <div className="w-56 shrink-0">
            <nav className="space-y-1 sticky top-8">
              {sections.map((section) => (
                <button
                  key={section.id}
                  onClick={() => {
                    setActiveSection(section.id);
                    // Clicking a sidebar item also clears any active search
                    // so the user can navigate freely. Without this, the
                    // searchQuery override would re-route them to FAQ.
                    setSearchQuery('');
                  }}
                  className={cn(
                    'w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors',
                    effectiveSection === section.id
                      ? 'bg-brand-500/20 text-brand-400'
                      : 'text-surface-400 hover:bg-surface-800 hover:text-surface-200'
                  )}
                >
                  <section.icon className="w-5 h-5" />
                  {section.title}
                </button>
              ))}

              {/* External links */}
              <div className="pt-4 border-t border-surface-800 mt-4 space-y-1">
                <a
                  href="https://scenemachine.ai/docs"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 px-3 py-2 text-surface-400 hover:text-surface-200 transition-colors"
                >
                  <ExternalLink className="w-5 h-5" />
                  {t('help.onlineDocs', 'Online Docs')}
                </a>
                <a
                  href="https://github.com/scenemachine/scenemachine/issues"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 px-3 py-2 text-surface-400 hover:text-surface-200 transition-colors"
                >
                  <MessageCircle className="w-5 h-5" />
                  {t('help.reportIssue', 'Report Issue')}
                </a>
              </div>
            </nav>
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="card">
              <h2 className="text-lg font-medium mb-6 flex items-center gap-2">
                {activeContent && (
                  <>
                    <activeContent.icon className="w-5 h-5 text-brand-400" />
                    {activeContent.title}
                  </>
                )}
              </h2>
              {activeContent?.content}
            </div>

            {/* Version info */}
            <div className="mt-6 text-center text-sm text-surface-500">
              <p>{t('help.versionInfo', 'SceneMachine Desktop v0.1.0')}</p>
              <p className="mt-1">{t('help.versionTagline', 'Built with AI for filmmakers and storytellers')}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default HelpPage;
