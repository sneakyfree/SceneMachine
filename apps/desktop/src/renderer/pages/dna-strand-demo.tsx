/**
 * DNA Strand Demo Page - Showcases all implemented DNA Strand features.
 *
 * Demonstrates the "A+ DNA Strand Master Plan" capabilities:
 * - TurboTax-style intake flow
 * - Multi-agent orchestration
 * - Blockers/Unlockers pattern
 * - Quality gating
 * - Production pipeline
 */

import { useState } from 'react';
import {
  Dna,
  FileText,
  Users,
  Video,
  Mic,
  Film,
  AlertTriangle,
  CheckCircle2,
  Play,
  Layers,
  Bot,
  Shield,
  ChevronRight,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useTranslation } from '../i18n/use-translation';
import { BlockersPanel } from '../components/blockers-panel';
import { ProductionDashboard } from '../components/production-dashboard';

// Feature card component
function FeatureCard({
  icon: Icon,
  title,
  description,
  status,
  onClick,
}: {
  icon: typeof Dna;
  title: string;
  description: string;
  status: 'ready' | 'active' | 'complete';
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-start gap-4 p-4 rounded-lg border transition-all text-left w-full',
        status === 'ready' && 'bg-surface-800 border-surface-700 hover:border-brand-500/50',
        status === 'active' && 'bg-brand-500/10 border-brand-500/50 ring-1 ring-brand-500/30',
        status === 'complete' && 'bg-green-500/10 border-green-500/50'
      )}
    >
      <div
        className={cn(
          'w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0',
          status === 'ready' && 'bg-surface-700 text-surface-300',
          status === 'active' && 'bg-brand-500 text-white',
          status === 'complete' && 'bg-green-500 text-white'
        )}
      >
        {status === 'complete' ? (
          <CheckCircle2 className="w-5 h-5" />
        ) : (
          <Icon className="w-5 h-5" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <h3 className="font-medium text-white">{title}</h3>
        <p className="text-sm text-surface-400 mt-1">{description}</p>
      </div>
      <ChevronRight
        className={cn(
          'w-5 h-5 mt-2 flex-shrink-0',
          status === 'active' ? 'text-brand-400' : 'text-surface-500'
        )}
      />
    </button>
  );
}

// Agent card for multi-agent visualization
function AgentCard({
  name,
  role,
  status,
  icon: Icon,
}: {
  name: string;
  role: string;
  status: 'idle' | 'working' | 'complete';
  icon: typeof Bot;
}) {
  return (
    <div
      className={cn(
        'p-3 rounded-lg border transition-all',
        status === 'idle' && 'bg-surface-800/50 border-surface-700/50 opacity-60',
        status === 'working' && 'bg-brand-500/10 border-brand-500/50 animate-pulse',
        status === 'complete' && 'bg-green-500/10 border-green-500/50'
      )}
    >
      <div className="flex items-center gap-2 mb-2">
        <Icon
          className={cn(
            'w-4 h-4',
            status === 'idle' && 'text-surface-500',
            status === 'working' && 'text-brand-400',
            status === 'complete' && 'text-green-400'
          )}
        />
        <span className="text-sm font-medium text-white">{name}</span>
      </div>
      <p className="text-xs text-surface-400">{role}</p>
    </div>
  );
}

// DNA Strand visualization
function DnaStrandVisualization() {
  return (
    <div className="relative h-48 flex items-center justify-center overflow-hidden">
      {/* Animated DNA helix */}
      <div className="relative w-64 h-full">
        {[...Array(8)].map((_, i) => (
          <div
            key={i}
            className="absolute left-1/2 -translate-x-1/2"
            style={{
              top: `${i * 12}%`,
              animation: `dnaRotate 3s ease-in-out infinite`,
              animationDelay: `${i * 0.15}s`,
            }}
          >
            <div className="flex items-center gap-8">
              <div
                className={cn(
                  'w-4 h-4 rounded-full',
                  i % 2 === 0 ? 'bg-brand-500' : 'bg-purple-500'
                )}
              />
              <div className="w-16 h-0.5 bg-gradient-to-r from-brand-500 via-white/30 to-purple-500" />
              <div
                className={cn(
                  'w-4 h-4 rounded-full',
                  i % 2 === 0 ? 'bg-purple-500' : 'bg-brand-500'
                )}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Glow effects */}
      <div className="absolute inset-0 bg-gradient-to-t from-surface-900 via-transparent to-surface-900 pointer-events-none" />
    </div>
  );
}

export function DnaStrandDemoPage() {
  const { t } = useTranslation();
  const [activeSection, setActiveSection] = useState<
    'overview' | 'blockers' | 'pipeline' | 'agents'
  >('overview');
  const [demoProjectId] = useState('demo-project-001');

  // Localized tab labels
  const sectionLabels: Record<'overview' | 'blockers' | 'pipeline' | 'agents', string> = {
    overview: t('dnaStrand.tabOverview', 'Overview'),
    blockers: t('dnaStrand.tabBlockers', 'Blockers'),
    pipeline: t('dnaStrand.tabPipeline', 'Pipeline'),
    agents: t('dnaStrand.tabAgents', 'Agents'),
  };

  // Simulated agent statuses
  const agents = [
    {
      name: t('dnaStrand.agentParserName', 'Parser Agent'),
      role: t('dnaStrand.agentParserRole', 'Screenplay analysis'),
      status: 'complete' as const,
      icon: FileText,
    },
    {
      name: t('dnaStrand.agentCharacterName', 'Character Agent'),
      role: t('dnaStrand.agentCharacterRole', 'Reference generation'),
      status: 'complete' as const,
      icon: Users,
    },
    {
      name: t('dnaStrand.agentGeneratorName', 'Generator Agent'),
      role: t('dnaStrand.agentGeneratorRole', 'Video generation'),
      status: 'working' as const,
      icon: Video,
    },
    {
      name: t('dnaStrand.agentAssemblerName', 'Assembler Agent'),
      role: t('dnaStrand.agentAssemblerRole', 'Scene composition'),
      status: 'idle' as const,
      icon: Film,
    },
    {
      name: t('dnaStrand.agentReviewerName', 'Reviewer Agent'),
      role: t('dnaStrand.agentReviewerRole', 'Quality assurance'),
      status: 'idle' as const,
      icon: Shield,
    },
  ];

  // DNA strand features
  const features = [
    {
      icon: FileText,
      title: t('dnaStrand.featureParserTitle', 'Screenplay Parser'),
      description: t(
        'dnaStrand.featureParserDesc',
        'FDX, Fountain, PDF support with LLM-powered shot breakdown'
      ),
      status: 'complete' as const,
    },
    {
      icon: Users,
      title: t('dnaStrand.featureCharacterTitle', 'Character Laboratory'),
      description: t(
        'dnaStrand.featureCharacterDesc',
        'Face embedding, voice cloning, AI reference generation'
      ),
      status: 'complete' as const,
    },
    {
      icon: AlertTriangle,
      title: t('dnaStrand.featureBlockersTitle', 'Blockers Engine'),
      description: t(
        'dnaStrand.featureBlockersDesc',
        '"Why Not + What To Do Next" pattern with auto-fix'
      ),
      status: 'complete' as const,
    },
    {
      icon: Video,
      title: t('dnaStrand.featureVideoTitle', 'Video Generation'),
      description: t(
        'dnaStrand.featureVideoDesc',
        'Multi-provider (Wan 2.1, Flux, Fal) with quality gating'
      ),
      status: 'active' as const,
    },
    {
      icon: Mic,
      title: t('dnaStrand.featureAudioTitle', 'Audio Pipeline'),
      description: t('dnaStrand.featureAudioDesc', '20 TTS voices, emotion support, lip-sync'),
      status: 'ready' as const,
    },
    {
      icon: Film,
      title: t('dnaStrand.featureAssemblyTitle', 'Assembly & Export'),
      description: t(
        'dnaStrand.featureAssemblyDesc',
        'FFmpeg composition with color grading, watermarks'
      ),
      status: 'ready' as const,
    },
  ];

  // Stats
  const stats = [
    { label: t('dnaStrand.statNewCode', 'New Code'), value: '6,200+', unit: t('dnaStrand.unitLines', 'lines') },
    { label: t('dnaStrand.statServices', 'Services'), value: '12', unit: t('dnaStrand.unitModules', 'modules') },
    { label: t('dnaStrand.statTtsVoices', 'TTS Voices'), value: '20', unit: t('dnaStrand.unitBuiltIn', 'built-in') },
    { label: t('dnaStrand.statQualityDims', 'Quality Dims'), value: '8', unit: t('dnaStrand.unitMetrics', 'metrics') },
  ];

  return (
    <div className="min-h-screen bg-surface-900 text-white">
      {/* Header */}
      <header className="border-b border-surface-700 bg-surface-800/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-brand-500 to-purple-500 flex items-center justify-center">
                <Dna className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold">{t('dnaStrand.headerTitle', 'DNA Strand Master Plan')}</h1>
                <p className="text-xs text-surface-400">{t('dnaStrand.headerSubtitle', 'SceneMachine A+ Implementation')}</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {(['overview', 'blockers', 'pipeline', 'agents'] as const).map((section) => (
                <button
                  key={section}
                  onClick={() => setActiveSection(section)}
                  className={cn(
                    'px-3 py-1.5 text-sm rounded-lg transition-colors capitalize',
                    activeSection === section
                      ? 'bg-brand-500 text-white'
                      : 'text-surface-400 hover:bg-surface-700'
                  )}
                >
                  {sectionLabels[section]}
                </button>
              ))}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {activeSection === 'overview' && (
          <div className="space-y-8">
            {/* Hero */}
            <div className="text-center py-8">
              <DnaStrandVisualization />
              <h2 className="text-3xl font-bold mt-4">
                {t('dnaStrand.heroTitle', 'Upload a Script → Click Generate → Download a Film')}
              </h2>
              <p className="text-surface-400 mt-2 max-w-2xl mx-auto">
                {t(
                  'dnaStrand.heroDescription',
                  'The complete DNA Strand implementation transforms screenplays into movies using multi-agent orchestration, quality gating, and human-in-the-loop approval.'
                )}
              </p>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {stats.map((stat) => (
                <div key={stat.label} className="bg-surface-800 rounded-lg p-4 text-center">
                  <p className="text-3xl font-bold text-brand-400">{stat.value}</p>
                  <p className="text-xs text-surface-400 mt-1">
                    {stat.label} <span className="text-surface-500">({stat.unit})</span>
                  </p>
                </div>
              ))}
            </div>

            {/* Feature grid */}
            <div className="grid md:grid-cols-2 gap-4">
              {features.map((feature) => (
                <FeatureCard key={feature.title} {...feature} />
              ))}
            </div>

            {/* Quick actions */}
            <div className="flex flex-wrap gap-4 justify-center pt-4">
              <button
                onClick={() => setActiveSection('blockers')}
                className="flex items-center gap-2 px-6 py-3 bg-yellow-500 hover:bg-yellow-600 text-black font-medium rounded-lg transition-colors"
              >
                <AlertTriangle className="w-5 h-5" />
                {t('dnaStrand.actionViewBlockers', 'View Blockers')}
              </button>
              <button
                onClick={() => setActiveSection('pipeline')}
                className="flex items-center gap-2 px-6 py-3 bg-brand-500 hover:bg-brand-600 text-white font-medium rounded-lg transition-colors"
              >
                <Play className="w-5 h-5" />
                {t('dnaStrand.actionProductionDashboard', 'Production Dashboard')}
              </button>
              <button
                onClick={() => setActiveSection('agents')}
                className="flex items-center gap-2 px-6 py-3 bg-purple-500 hover:bg-purple-600 text-white font-medium rounded-lg transition-colors"
              >
                <Bot className="w-5 h-5" />
                {t('dnaStrand.actionAgentCrew', 'Agent Crew')}
              </button>
            </div>
          </div>
        )}

        {activeSection === 'blockers' && (
          <div className="bg-surface-800 rounded-lg border border-surface-700 overflow-hidden">
            <BlockersPanel projectId={demoProjectId} />
          </div>
        )}

        {activeSection === 'pipeline' && (
          <div className="bg-surface-800 rounded-lg border border-surface-700 overflow-hidden">
            <ProductionDashboard projectId={demoProjectId} />
          </div>
        )}

        {activeSection === 'agents' && (
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-2xl font-bold">{t('dnaStrand.agentsHeading', 'Agentic Crew')}</h2>
              <p className="text-surface-400 mt-2">
                {t(
                  'dnaStrand.agentsSubheading',
                  '5 specialized agents work together with bounded autonomy'
                )}
              </p>
            </div>

            {/* Agent grid */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {agents.map((agent) => (
                <AgentCard key={agent.name} {...agent} />
              ))}
            </div>

            {/* Architecture diagram */}
            <div className="bg-surface-800 rounded-lg border border-surface-700 p-6">
              <h3 className="text-lg font-medium mb-4 flex items-center gap-2">
                <Layers className="w-5 h-5 text-brand-400" />
                {t('dnaStrand.architectureTitle', 'Multi-Agent Architecture')}
              </h3>
              <div className="grid md:grid-cols-3 gap-4">
                <div className="p-4 bg-surface-700/50 rounded-lg">
                  <h4 className="font-medium text-brand-400 mb-2">{t('dnaStrand.layer1Title', 'Layer 1: Orchestrator')}</h4>
                  <ul className="text-sm text-surface-400 space-y-1">
                    <li>• {t('dnaStrand.layer1Item1', 'Workflow coordination')}</li>
                    <li>• {t('dnaStrand.layer1Item2', 'Agent delegation')}</li>
                    <li>• {t('dnaStrand.layer1Item3', 'State management')}</li>
                  </ul>
                </div>
                <div className="p-4 bg-surface-700/50 rounded-lg">
                  <h4 className="font-medium text-purple-400 mb-2">{t('dnaStrand.layer2Title', 'Layer 2: Specialists')}</h4>
                  <ul className="text-sm text-surface-400 space-y-1">
                    <li>• {t('dnaStrand.agentParserName', 'Parser Agent')}</li>
                    <li>• {t('dnaStrand.agentCharacterName', 'Character Agent')}</li>
                    <li>• {t('dnaStrand.agentGeneratorName', 'Generator Agent')}</li>
                    <li>• {t('dnaStrand.agentAssemblerName', 'Assembler Agent')}</li>
                    <li>• {t('dnaStrand.agentReviewerName', 'Reviewer Agent')}</li>
                  </ul>
                </div>
                <div className="p-4 bg-surface-700/50 rounded-lg">
                  <h4 className="font-medium text-green-400 mb-2">{t('dnaStrand.layer3Title', 'Layer 3: Guardrails')}</h4>
                  <ul className="text-sm text-surface-400 space-y-1">
                    <li>• {t('dnaStrand.layer3Item1', 'Approval gates')}</li>
                    <li>• {t('dnaStrand.layer3Item2', 'Budget limits')}</li>
                    <li>• {t('dnaStrand.layer3Item3', 'Quality thresholds')}</li>
                    <li>• {t('dnaStrand.layer3Item4', 'Action logging')}</li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Bounded autonomy explanation */}
            <div className="bg-gradient-to-r from-brand-500/10 to-purple-500/10 rounded-lg border border-brand-500/30 p-6">
              <h3 className="text-lg font-medium mb-3 flex items-center gap-2">
                <Shield className="w-5 h-5 text-brand-400" />
                {t('dnaStrand.boundedAutonomyTitle', 'Bounded Autonomy')}
              </h3>
              <div className="grid md:grid-cols-4 gap-4 text-sm">
                <div className="p-3 bg-surface-900/50 rounded">
                  <p className="font-medium text-green-400">{t('dnaStrand.tier0Title', 'Tier 0: Auto')}</p>
                  <p className="text-surface-400 mt-1">{t('dnaStrand.tier0Desc', 'Minor decisions like prompt refinement')}</p>
                </div>
                <div className="p-3 bg-surface-900/50 rounded">
                  <p className="font-medium text-blue-400">{t('dnaStrand.tier1Title', 'Tier 1: Notify')}</p>
                  <p className="text-surface-400 mt-1">{t('dnaStrand.tier1Desc', 'User informed but not blocked')}</p>
                </div>
                <div className="p-3 bg-surface-900/50 rounded">
                  <p className="font-medium text-yellow-400">{t('dnaStrand.tier2Title', 'Tier 2: Approval')}</p>
                  <p className="text-surface-400 mt-1">{t('dnaStrand.tier2Desc', 'Requires explicit user approval')}</p>
                </div>
                <div className="p-3 bg-surface-900/50 rounded">
                  <p className="font-medium text-red-400">{t('dnaStrand.tier3Title', 'Tier 3: Blocked')}</p>
                  <p className="text-surface-400 mt-1">{t('dnaStrand.tier3Desc', 'Cannot proceed without intervention')}</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* CSS for DNA animation */}
      <style>{`
        @keyframes dnaRotate {
          0%, 100% { transform: translateX(-50%) rotateY(0deg); }
          50% { transform: translateX(-50%) rotateY(180deg); }
        }
      `}</style>
    </div>
  );
}

export default DnaStrandDemoPage;
