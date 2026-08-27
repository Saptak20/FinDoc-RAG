import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { User, Sparkles, AlertCircle, Copy, Check } from 'lucide-react';
import type { Message } from '../types/chat';
import { SourceDrawer } from './SourceDrawer';
import { TechnicalDetails } from './TechnicalDetails';

interface ChatMessageProps {
  message: Message;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const [copied, setCopied] = React.useState(false);
  const isUser = message.role === 'user';

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isUser) {
    return (
      <div className="flex justify-end mb-5 animate-slide-up">
        <div className="flex items-start gap-2.5 max-w-[75%] lg:max-w-[65%]">
          <div className="bg-void-800/60 backdrop-blur-xl rounded-2xl rounded-tr-md px-4 py-3 border border-void-700/30 shadow-glass-1">
            <p className="text-body-sm font-normal whitespace-pre-wrap leading-relaxed text-ui-text">
              {message.content}
            </p>
          </div>
          <div className="w-8 h-8 rounded-full bg-void-800/50 border border-void-700/50 flex items-center justify-center shrink-0">
            <User className="w-4 h-4 text-ui-text-subtle" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start mb-6 animate-slide-up">
      <div className="flex items-start gap-3 max-w-full w-full">
        {/* Assistant Avatar - Subtle */}
        <div className="relative shrink-0 mt-0.5">
          <div className="w-8 h-8 rounded-xl bg-void-800/50 border border-void-700/50 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-accent-emerald" />
          </div>
        </div>

        {/* Response Body */}
        <div className="flex-1 bg-void-800/40 backdrop-blur-xl rounded-2xl rounded-tl-xl p-4 lg:p-5 border border-void-700/30 shadow-glass-1">
          {message.isError ? (
            <div className="flex items-start gap-3 text-accent-rose text-body-sm">
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold mb-1">Inference Notice</p>
                <p className="text-caption text-accent-rose/90 leading-relaxed">{message.content}</p>
              </div>
            </div>
          ) : (
            <>
              {/* Top Meta Bar - Minimal */}
              <div className="flex items-center justify-between mb-3 pb-2.5 border-b border-void-700/30">
                <div className="flex items-center gap-1.5">
                  <span className="text-micro font-mono font-medium tracking-wider text-ui-text-subtle uppercase">
                    Financial Insight
                  </span>
                </div>
                <button
                  onClick={handleCopy}
                  title="Copy response"
                  className="btn-ghost p-1 rounded-lg text-caption font-mono opacity-60 hover:opacity-100"
                >
                  {copied ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-accent-emerald" />
                      <span className="text-accent-emerald ml-1">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span className="ml-1">Copy</span>
                    </>
                  )}
                </button>
              </div>

              {/* Rendered Markdown Answer */}
              <div className="prose-financial text-body-sm mb-5">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {message.content}
                </ReactMarkdown>
              </div>

              {/* Documentary Evidence Sources */}
              {message.sources && message.sources.length > 0 && (
                <SourceDrawer sources={message.sources} />
              )}

              {/* Pipeline Telemetry Details */}
              {message.metrics && (
                <TechnicalDetails metrics={message.metrics} />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};