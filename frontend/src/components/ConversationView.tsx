import React from 'react';
import { ChatMessage } from './ChatMessage';
import type { Message } from '../types/chat';

interface ConversationViewProps {
  messages: Message[];
  isLoading: boolean;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
  onSelectPrompt: (prompt: string) => void;
}

export const ConversationView: React.FC<ConversationViewProps> = ({
  messages,
  isLoading,
  messagesEndRef,
  onSelectPrompt,
}) => {
  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 lg:p-12">
        {/* Empty State - Minimal */}
        <div className="w-full max-w-2xl text-center animate-fade-in">
          {/* Headline */}
          <h1 className="font-display font-bold text-display-lg tracking-tight text-ui-text mb-4 leading-[1.05]">
            Ask anything about your financial documents
          </h1>

          {/* Subtitle */}
          <p className="text-body-lg text-ui-text-muted mb-10 max-w-lg mx-auto leading-relaxed">
            Every answer is grounded in your documents with verifiable citations, cross-encoder reranking, and full pipeline transparency.
          </p>

          {/* Example Prompts - lightweight text links */}
          <div className="space-y-2.5 mb-12">
            <p className="text-micro font-mono uppercase tracking-wider text-ui-text-subtle">Example questions</p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              {[
                "What was Tata Steel's EBITDA margin in FY2023-24?",
                "What is the Net Zero carbon emissions target year?",
                "What were Shikhar25 project savings in FY2023-24?",
              ].map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => onSelectPrompt(q)}
                  className="text-left px-4 py-3 rounded-xl bg-void-800/50 border border-void-700/50 hover:bg-void-800/80 hover:border-void-600/50 transition-all duration-150 text-body-sm text-ui-text"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 lg:p-6 space-y-5">
      <div className="container-main">
        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}
        <div ref={messagesEndRef} />
        {isLoading && (
          <div className="flex items-center justify-center py-8 animate-fade-in">
            <div className="flex items-center gap-3 text-ui-text-muted">
              <svg className="w-5 h-5 text-accent-emerald animate-spin" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span className="text-body-sm font-medium">Synthesizing answer…</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};