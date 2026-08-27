import React, { useState } from 'react';
import { FileText, Bookmark, ShieldCheck, ChevronDown, ChevronUp, Hash, Copy, Check } from 'lucide-react';
import type { SourceItem } from '../types/chat';

interface SourceDrawerProps {
  sources: SourceItem[];
}

export const SourceDrawer: React.FC<SourceDrawerProps> = ({ sources }) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [copiedChunkId, setCopiedChunkId] = useState<string | null>(null);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="bg-void-800/30 backdrop-blur-xl rounded-xl p-4 lg:p-5 border border-void-700/30 animate-slide-up">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Bookmark className="w-4 h-4 text-accent-emerald" />
          <span className="text-micro font-mono font-semibold text-ui-text tracking-wider uppercase">
            Sources ({sources.length})
          </span>
        </div>
        <span className="text-micro font-mono text-ui-text-subtle hidden sm:inline">
          Cross-Encoder scored
        </span>
      </div>

      <div className="space-y-2">
        {sources.map((src, index) => {
          const isExpanded = expandedId === src.chunk_id;
          const score = src.rerank_score;
          const isHighRelevance = score !== undefined && score !== null && score > 4.0;

          return (
            <div
              key={src.chunk_id || index}
              className={`rounded-xl border transition-all duration-150 ${
                isExpanded
                  ? 'bg-void-800/60 border-accent-emerald/20 shadow-glass-1'
                  : 'bg-void-900/30 border-void-700/40 hover:bg-void-800/40 hover:border-void-600/40'
              }`}
            >
              <div className="p-3">
                {/* Header with Filename & Page Badge */}
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2 overflow-hidden">
                    <FileText className="w-3.5 h-3.5 text-accent-emerald flex-shrink-0" />
                    <span className="font-medium text-body-sm text-ui-text truncate" title={src.source}>
                      {src.source}
                    </span>
                  </div>
                  <span className="px-2 py-0.5 rounded text-micro font-mono font-medium bg-accent-emerald/10 text-accent-emerald border border-accent-emerald/20 shrink-0">
                    Page {src.page}
                  </span>
                </div>

                {/* Relevance & Score */}
                <div className="flex items-center justify-between text-caption text-ui-text-subtle mb-2">
                  <div className="flex items-center gap-1">
                    <ShieldCheck className="w-3 h-3 text-accent-emerald" />
                    <span className="text-caption font-medium text-ui-text">
                      {isHighRelevance ? 'High Relevance' : 'Corroborating'}
                    </span>
                  </div>
                  <span className="font-mono text-caption font-medium" style={{ color: score !== undefined && score !== null ? 'var(--color-accent-emerald)' : 'var(--color-accent-cyan)' }}>
                    {score !== undefined && score !== null ? `+${score.toFixed(2)}` : 'RRF'}
                  </span>
                </div>

                {/* Toggle Chunk Details */}
                <button
                  onClick={() => setExpandedId(expandedId === src.chunk_id ? null : src.chunk_id)}
                  className="w-full flex items-center justify-between py-1.5 border-t border-void-700/30 text-caption font-mono text-ui-text-subtle hover:text-accent-emerald transition-colors"
                >
                  <span>Chunk citation</span>
                  <span className="flex items-center gap-1">
                    <Hash className="w-3 h-3" />
                    {isExpanded ? (
                      <>
                        <span>Hide</span>
                        <ChevronUp className="w-3 h-3" />
                      </>
                    ) : (
                      <>
                        <span>Inspect</span>
                        <ChevronDown className="w-3 h-3" />
                      </>
                    )}
                  </span>
                </button>

                {isExpanded && (
                  <div className="border-t border-accent-emerald/15 p-3 bg-void-900/40 rounded-b-xl animate-slide-up">
                    <div className="space-y-2 text-caption font-mono">
                      <div className="flex items-center gap-2">
                        <span className="text-ui-text-subtle">Chunk ID</span>
                        <div className="flex-1 flex items-center gap-2">
                          <span className="text-accent-emerald select-all break-all leading-tight text-micro">{src.chunk_id}</span>
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(src.chunk_id);
                              setCopiedChunkId(src.chunk_id);
                              setTimeout(() => setCopiedChunkId(null), 2000);
                            }}
                            className="btn-icon p-1 rounded text-ui-text-subtle hover:text-accent-emerald"
                            title="Copy chunk ID"
                          >
                            {copiedChunkId === src.chunk_id ? (
                              <Check className="w-3.5 h-3.5 text-accent-emerald" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>
                      </div>
                      {src.rrf_score && (
                        <div className="flex justify-between text-ui-text-subtle">
                          <span>RRF Fusion Score</span>
                          <span className="font-mono font-bold text-body-sm text-ui-text">{src.rrf_score.toFixed(4)}</span>
                        </div>
                      )}
                      {src.retrieval_sources && src.retrieval_sources.length > 0 && (
                        <div className="flex items-center gap-1.5">
                          <span className="text-ui-text-subtle">Via</span>
                          <div className="flex items-center gap-1">
                            {src.retrieval_sources.map((s, i) => (
                              <span key={i} className="px-1.5 py-0.5 rounded text-micro font-mono bg-void-700/50 text-ui-text-subtle border border-void-600/30">
                                {s === 'faiss' ? 'FAISS' : s === 'bm25' ? 'BM25' : s}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default SourceDrawer;