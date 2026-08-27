import React, { useState, useRef, useEffect } from 'react';
import { Send, SlidersHorizontal, Trash2, Loader2, Layers, Cpu, Sparkles } from 'lucide-react';

interface ComposerProps {
  onSendMessage: (query: string, params: { dense_top_k: number; sparse_top_k: number; final_top_k: number }) => void;
  isLoading: boolean;
  onClearChat: () => void;
  hasMessages: boolean;
  initialPrompt?: string;
  onPromptUsed?: () => void;
}

export const Composer: React.FC<ComposerProps> = ({
  onSendMessage,
  isLoading,
  onClearChat,
  hasMessages,
  initialPrompt,
  onPromptUsed,
}) => {
  const [query, setQuery] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [denseTopK, setDenseTopK] = useState(10);
  const [sparseTopK, setSparseTopK] = useState(10);
  const [finalTopK, setFinalTopK] = useState(3);
  const [loadingStep, setLoadingStep] = useState(0);

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Multi-stage progressive inference status
  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    if (isLoading) {
      setLoadingStep(0);
      interval = setInterval(() => {
        setLoadingStep((prev) => (prev < 2 ? prev + 1 : prev));
      }, 1200);
    }
    return () => clearInterval(interval);
  }, [isLoading]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 240)}px`;
    }
  }, [query]);

  // Populate textarea with initial prompt when provided
  useEffect(() => {
    if (initialPrompt && !query) {
      setQuery(initialPrompt);
      onPromptUsed?.();
    }
  }, [initialPrompt, query, onPromptUsed]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim() || isLoading) return;

    onSendMessage(query, {
      dense_top_k: denseTopK,
      sparse_top_k: sparseTopK,
      final_top_k: finalTopK,
    });
    setQuery('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const stages = [
    { label: 'Hybrid Retrieval', icon: <Layers className="w-3.5 h-3.5" /> },
    { label: 'Cross-Encoder Scoring', icon: <Cpu className="w-3.5 h-3.5" /> },
    { label: 'Grounded Synthesis', icon: <Sparkles className="w-3.5 h-3.5" /> },
  ];

  return (
    <div className="relative z-[200] bg-gradient-to-t from-void-950 via-void-950/90 to-transparent pt-3 pb-4 px-4 lg:pb-6 lg:px-6">
      <div className="container-main">
        {/* Loading Banner - Compact */}
        {isLoading && (
          <div className="mb-3 glass-surface rounded-xl p-3 animate-slide-up">
            <div className="flex items-center gap-2.5">
              <Loader2 className="w-4 h-4 text-accent-emerald animate-spin flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-caption font-semibold text-accent-emerald">
                  Stage {loadingStep + 1} of 3
                </p>
                <p className="text-body-sm font-medium text-ui-text truncate">
                  {stages[loadingStep]?.label}
                </p>
              </div>
              <div className="flex items-center gap-1 hidden sm:flex">
                {stages.map((_, idx) => (
                  <div
                    key={idx}
                    className={`h-1 rounded-full transition-all duration-300 ease-spring ${
                      idx === loadingStep
                        ? 'w-8 bg-accent-emerald'
                        : idx < loadingStep
                        ? 'w-5 bg-accent-emerald/60'
                        : 'w-3 bg-void-700/50'
                    }`}
                  />
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Retrieval Parameters Dropdown */}
        {showSettings && (
          <div className="mb-3 glass-surface rounded-xl p-3 animate-slide-up grid grid-cols-3 gap-3">
            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <span className="text-caption font-medium text-ui-text-muted">Dense (FAISS)</span>
                <span className="font-mono font-bold text-accent-emerald text-body-sm">{denseTopK}</span>
              </div>
              <input
                type="range"
                min="3"
                max="25"
                value={denseTopK}
                onChange={(e) => setDenseTopK(Number(e.target.value))}
                className="w-full accent-accent-emerald cursor-pointer h-1 bg-void-700/50 rounded-lg appearance-none"
              />
              <span className="text-micro text-ui-text-subtle">768-D semantic cosine search</span>
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <span className="text-caption font-medium text-ui-text-muted">Sparse (BM25)</span>
                <span className="font-mono font-bold text-accent-cyan text-body-sm">{sparseTopK}</span>
              </div>
              <input
                type="range"
                min="3"
                max="25"
                value={sparseTopK}
                onChange={(e) => setSparseTopK(Number(e.target.value))}
                className="w-full accent-accent-cyan cursor-pointer h-1 bg-void-700/50 rounded-lg appearance-none"
              />
              <span className="text-micro text-ui-text-subtle">Exact lexical term frequency</span>
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <span className="text-caption font-medium text-ui-text-muted">Final Context</span>
                <span className="font-mono font-bold text-accent-violet text-body-sm">{finalTopK}</span>
              </div>
              <input
                type="range"
                min="1"
                max="10"
                value={finalTopK}
                onChange={(e) => setFinalTopK(Number(e.target.value))}
                className="w-full accent-accent-violet cursor-pointer h-1 bg-void-700/50 rounded-lg appearance-none"
              />
              <span className="text-micro text-ui-text-subtle">Cross-Encoder reranked evidence</span>
            </div>
          </div>
        )}

        {/* Main Input */}
        <form onSubmit={handleSubmit} className="relative">
          <div className="glass-surface rounded-xl border border-void-700/50 focus-within:border-accent-emerald/50 focus-within:ring-2 focus-within:ring-accent-emerald/20 transition-all duration-150 overflow-hidden">
            {/* Toolbar - Compact */}
            <div className="flex items-center gap-1 p-1.5 border-b border-void-700/30">
              <button
                type="button"
                onClick={() => setShowSettings(!showSettings)}
                title="Configure retrieval parameters"
                className={`btn-icon p-1.5 rounded-lg transition-all ${showSettings
                  ? 'bg-accent-emerald/10 text-accent-emerald border-accent-emerald/20'
                  : 'hover:bg-void-800/50'}`}
              >
                <SlidersHorizontal className="w-4 h-4" />
              </button>

              {hasMessages && (
                <button
                  type="button"
                  onClick={onClearChat}
                  title="Clear conversation"
                  className="btn-icon p-1.5 rounded-lg text-ui-text-muted hover:text-accent-rose hover:bg-accent-rose/5"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}

              <div className="flex-1" />

              {/* Quick parameter display */}
              <div className="hidden lg:flex items-center gap-2 text-micro font-mono text-ui-text-subtle">
                <span className="px-1.5 py-0.5 rounded bg-void-700/50 text-accent-emerald">
                  Dense: {denseTopK}
                </span>
                <span className="px-1.5 py-0.5 rounded bg-void-700/50 text-accent-cyan">
                  Sparse: {sparseTopK}
                </span>
                <span className="px-1.5 py-0.5 rounded bg-void-700/50 text-accent-violet">
                  Final: {finalTopK}
                </span>
              </div>
            </div>

            {/* Textarea - Taller */}
            <div className="p-2 lg:p-3">
              <textarea
                ref={textareaRef}
                rows={1}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a financial question about revenues, EBITDA margins, ESG targets, balance sheet…"
                disabled={isLoading}
                className="w-full bg-transparent text-ui-text placeholder-ui-text-subtle text-body resize-none min-h-[56px] max-h-[240px] leading-relaxed disabled:opacity-50 focus:outline-none font-sans"
                style={{ lineHeight: 1.7 }}
                aria-label="Financial question"
              />
            </div>

            {/* Submit Bar - Compact */}
            <div className="flex items-center justify-end gap-2 p-1.5 lg:p-2 border-t border-void-700/30 bg-void-900/30">
              <div className="hidden sm:flex items-center gap-1.5 text-micro text-ui-text-subtle">
                <kbd className="px-1 py-0.5 rounded bg-void-700/50 border border-void-600/50 font-mono">Enter</kbd>
                <span>to send</span>
                <span className="w-px h-3 bg-void-700/50" />
                <kbd className="px-1 py-0.5 rounded bg-void-700/50 border border-void-600/50 font-mono">⇧ Shift + Enter</kbd>
                <span>for new line</span>
              </div>

              <button
                type="submit"
                disabled={!query.trim() || isLoading}
                className="btn-primary px-4 py-2 rounded-xl min-w-[88px]"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Working…</span>
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    <span>Send</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};