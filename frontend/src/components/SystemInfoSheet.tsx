import React, { useState } from 'react';
import { X, Cpu, Layers, Sparkles, Server, CheckCircle2, ArrowDown, ChevronDown, FileText } from 'lucide-react';
import type { SystemStatus } from '../types/chat';

interface SystemInfoSheetProps {
  isOpen: boolean;
  onClose: () => void;
  status: SystemStatus;
}

export const SystemInfoSheet: React.FC<SystemInfoSheetProps> = ({ isOpen, onClose, status }) => {
  const [expandedStage, setExpandedStage] = useState<number | null>(0);

  const stages = [
    {
      number: '01',
      title: 'Query Ingestion',
      subtitle: 'Pydantic Validated',
      color: 'accent-emerald',
      icon: Cpu,
      description: 'Financial query intake with bounds checking and user-configurable dense/sparse candidate thresholds.',
      details: [
        { label: 'Validation', value: 'FastAPI + Pydantic v2' },
        { label: 'Rate Limits', value: '30/min chat, 10/min upload/delete' },
        { label: 'Request ID', value: 'X-Request-ID correlation' },
      ],
    },
    {
      number: '02',
      title: 'Dual Hybrid Retrieval',
      subtitle: 'FAISS + BM25Okapi',
      color: 'accent-cyan',
      icon: Layers,
      description: 'Parallel dense semantic search and sparse lexical search for comprehensive candidate coverage.',
      details: [
        { label: 'Dense Search', value: 'FAISS 768-D (nomic-embed-text)' },
        { label: 'Sparse Search', value: 'BM25Okapi on 2,710+ chunks' },
        { label: 'Candidates', value: 'Top 10 each (configurable)' },
      ],
    },
    {
      number: '03',
      title: 'Rank Fusion & Reranking',
      subtitle: 'Transformer Scored',
      color: 'accent-violet',
      icon: Sparkles,
      description: 'Reciprocal Rank Fusion deduplicates by chunk_id, then Cross-Encoder pairwise scoring filters to top evidence.',
      details: [
        { label: 'RRF Parameter', value: 'k = 60' },
        { label: 'Cross-Encoder', value: 'ms-marco-MiniLM-L-6-v2' },
        { label: 'Final Top-K', value: '3 chunks (configurable)' },
      ],
    },
    {
      number: '04',
      title: 'Grounded Synthesis & Telemetry',
      subtitle: 'Ollama + PostgreSQL',
      color: 'accent-amber',
      icon: Server,
      description: 'LangGraph-orchestrated prompt construction with zero hallucinations outside context. Async query logging.',
      details: [
        { label: 'LLM', value: 'llama3.2:3b (local)' },
        { label: 'Orchestration', value: 'LangGraph StateGraph' },
        { label: 'Logging', value: 'Async PostgreSQL persistence' },
      ],
    },
  ];

  if (!isOpen) return null;

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 z-[400] bg-void-950/80 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Sheet Panel */}
      <div
        className="fixed inset-y-0 right-0 z-[400] w-full max-w-2xl lg:max-w-3xl bg-void-900 border-l border-void-700 shadow-glass-3 animate-slide-in-right flex flex-col overflow-hidden"
        role="dialog"
        aria-modal="true"
        aria-labelledby="system-info-title"
      >
        {/* Header */}
        <div className="flex items-center justify-between h-12 px-4 lg:px-5 border-b border-void-700">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-accent-emerald/10 flex items-center justify-center">
              <Cpu className="w-4.5 h-4.5 text-accent-emerald" />
            </div>
            <div>
              <h2 id="system-info-title" className="font-display font-semibold text-body-sm tracking-tight text-ui-text">
                System Architecture
              </h2>
              <p className="text-micro text-ui-text-subtle">
                Multi-Stage Hybrid Retrieval & Grounded Reasoning
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="btn-icon"
            aria-label="Close architecture view"
          >
            <X className="w-4.5 h-4.5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 lg:p-5 space-y-3">
          {/* Status Overview */}
          <div className="bg-void-800/40 backdrop-blur-xl rounded-xl p-3 border border-void-700/30">
            <div className="flex items-center justify-between mb-2">
              <span className="text-micro font-mono uppercase tracking-wider text-ui-text-subtle">
                System Status
              </span>
              <span className={`badge ${status.status === 'ready' ? 'badge-success' :
                                        status.status === 'healthy' ? 'badge-info' :
                                        status.status === 'checking' ? 'badge-warning' :
                                        status.status === 'not_ready' ? 'badge-warning' :
                                        'badge-error'}`}>
                <span className="flex items-center gap-1">
                  <span className={`status-dot ${status.status === 'ready' ? 'status-ready' :
                                            status.status === 'healthy' ? 'status-healthy' :
                                            status.status === 'checking' ? 'status-checking' :
                                            status.status === 'not_ready' ? 'status-degraded' :
                                            'status-offline'}`} />
                  {status.status === 'ready' ? 'Ready' :
                   status.status === 'healthy' ? 'Healthy' :
                   status.status === 'checking' ? 'Checking…' :
                   status.status === 'not_ready' ? 'Degraded' : 'Offline'}
                </span>
              </span>
            </div>

            {status.checks && (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                {[
                  { key: 'faiss_index', label: 'FAISS Index', icon: Layers },
                  { key: 'chunk_corpus', label: 'Chunk Corpus', icon: FileText },
                  { key: 'ollama_service', label: 'Ollama Service', icon: Server },
                ].map((check) => (
                  <div key={check.key} className="bg-void-900/40 rounded-lg p-2.5 flex items-center gap-2">
                    <check.icon className="w-4 h-4 text-accent-emerald" />
                    <div>
                      <p className="text-micro text-ui-text-subtle">{check.label}</p>
                      <p className="font-mono text-caption">
                        {status.checks?.[check.key as keyof typeof status.checks] ? (
                          <span className="text-accent-emerald">● Ready</span>
                        ) : (
                          <span className="text-accent-rose">○ Unavailable</span>
                        )}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Pipeline Stages */}
          <div className="space-y-2">
            {stages.map((stage, index) => (
              <div key={index} className="group">
                {/* Stage Header */}
                <button
                  onClick={() => setExpandedStage(expandedStage === index ? null : index)}
                  className="w-full bg-void-800/30 hover:bg-void-800/50 rounded-xl p-3 lg:p-4 flex items-start gap-3 transition-all duration-150 border border-void-700/30"
                >
                  <div className="flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center"
                    style={{ backgroundColor: `var(--color-${stage.color}Dim)` }}>
                    <stage.icon className="w-5 h-5" style={{ color: `var(--color-${stage.color})` }} />
                  </div>
                  <div className="flex-1 min-w-0 pt-0.5">
                    <div className="flex items-center justify-between gap-2 mb-0.5">
                      <div className="flex items-center gap-1.5">
                        <span className="text-micro font-mono uppercase tracking-wider font-semibold"
                          style={{ color: `var(--color-${stage.color})` }}>
                          Stage {stage.number}
                        </span>
                        <span className="px-1.5 py-0.5 rounded text-micro font-mono"
                          style={{ backgroundColor: `var(--color-${stage.color}Dim)`, color: `var(--color-${stage.color})`, borderColor: `var(--color-${stage.color})` }}>
                          {stage.subtitle}
                        </span>
                      </div>
                      <ChevronDown className={`w-4.5 h-4.5 text-ui-text-subtle transition-transform duration-150 flex-shrink-0 ${expandedStage === index ? 'rotate-180' : ''}`} />
                    </div>
                    <p className="text-body-sm text-ui-text-muted leading-relaxed pr-8">
                      {stage.description}
                    </p>
                  </div>
                </button>

                {/* Expanded Details */}
                {expandedStage === index && (
                  <div className="animate-slide-up ml-12 lg:ml-0 border-l border-void-700/30 pl-3 lg:pl-0 mt-1">
                    <div className="bg-void-800/40 backdrop-blur-xl rounded-xl p-3 lg:p-4 mt-1.5 space-y-2">
                      <p className="text-micro font-mono uppercase tracking-wider text-ui-text-subtle">Technical Details</p>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {stage.details.map((detail, dIdx) => (
                          <div key={dIdx} className="bg-void-900/40 rounded-lg p-2.5">
                            <p className="text-micro font-mono uppercase tracking-wider text-ui-text-subtle mb-0.5">
                              {detail.label}
                            </p>
                            <p className="font-mono text-body-sm text-ui-text">{detail.value}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Connector Arrow */}
                {index < stages.length - 1 && (
                  <div className="flex justify-center">
                    <ArrowDown className="w-4 h-4 text-void-700/50 group-hover:text-accent-emerald/50 transition-colors" />
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Footer Info */}
          <div className="bg-void-800/40 backdrop-blur-xl rounded-xl p-3 border border-void-700/30 border-l-2 border-accent-emerald">
            <div className="flex items-center gap-1.5 text-micro text-accent-emerald mb-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span className="font-mono font-medium">Target Corpus</span>
            </div>
            <p className="text-body-sm text-ui-text-muted">
              Tata Steel 117th Integrated Report FY2023-24 (581 Pages, 2,710 Chunks)
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 lg:p-4 border-t border-void-700/30">
          <button
            onClick={onClose}
            className="w-full lg:w-auto btn-primary justify-center px-4 py-2"
          >
            Close
          </button>
        </div>
      </div>
    </>
  );
};