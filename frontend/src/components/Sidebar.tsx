import React, { useEffect, useRef } from 'react';
import { X, MessageSquare, FileSpreadsheet, Sparkles, Clock } from 'lucide-react';
import type { Message, DocumentItem } from '../types/chat';
import { format } from 'date-fns';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onNewChat: () => void;
  messages: Message[];
  documents: DocumentItem[];
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  onClose,
  onNewChat,
  messages,
  documents,
}) => {
  const sidebarRef = useRef<HTMLDivElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Handle click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (isOpen && sidebarRef.current && !sidebarRef.current.contains(e.target as Node) &&
          overlayRef.current && !overlayRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen, onClose]);

  // Group messages by conversation (simple grouping - each assistant response ends a conversation segment)
  const getConversationPreviews = () => {
    const previews: { id: string; title: string; time: string; messageCount: number }[] = [];
    let currentConversation: Message[] = [];

    messages.forEach((msg, index) => {
      currentConversation.push(msg);
      if (msg.role === 'assistant' || index === messages.length - 1) {
        if (currentConversation.length > 0) {
          const firstUserMsg = currentConversation.find(m => m.role === 'user');
          previews.push({
            id: `conv-${index}`,
            title: firstUserMsg?.content.slice(0, 50) + (firstUserMsg && firstUserMsg.content.length > 50 ? '…' : '') || 'New conversation',
            time: format(new Date(currentConversation[0].timestamp), 'HH:mm'),
            messageCount: currentConversation.length,
          });
          currentConversation = [];
        }
      }
    });

    return previews.slice(-10).reverse(); // Last 10 conversations, newest first
  };

  const conversationPreviews = getConversationPreviews();
  const readyDocs = documents.filter(d => d.processing_status === 'READY').length;

  if (!isOpen) return null;

  return (
    <>
      {/* Overlay for mobile */}
      <div
        ref={overlayRef}
        className="fixed inset-0 z-[300] bg-void-950/80 backdrop-blur-sm animate-fade-in lg:hidden"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Sidebar Panel */}
      <aside
        ref={sidebarRef}
        className="fixed inset-y-0 left-0 z-[300] w-72 lg:w-80 bg-void-900 border-r border-void-700 shadow-glass-3 animate-slide-in-right flex flex-col overflow-hidden"
        role="complementary"
        aria-label="Navigation"
      >
        {/* Header */}
        <div className="flex items-center justify-between h-14 px-4 border-b border-void-700">
          <div className="flex items-center gap-2.5">
            <span className="font-display font-semibold text-body tracking-tight text-ui-text">
              FinDoc<span className="text-accent-emerald font-mono font-medium">-RAG</span>
            </span>
          </div>
          <button
            onClick={onClose}
            className="btn-icon"
            aria-label="Close sidebar"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {/* New Chat */}
          <button
            onClick={onNewChat}
            className="w-full btn-secondary justify-start gap-3 px-3 py-2.5 rounded-xl transition-all duration-150"
          >
            <div className="w-8 h-8 rounded-xl bg-accent-emerald/10 flex items-center justify-center flex-shrink-0">
              <Sparkles className="w-4.5 h-4.5 text-accent-emerald" />
            </div>
            <span className="text-body-sm font-medium text-ui-text">New Conversation</span>
          </button>

          {/* Conversation History */}
          {conversationPreviews.length > 0 && (
            <section>
              <h3 className="text-micro font-mono uppercase tracking-wider text-ui-text-subtle px-2 mb-2">
                Recent Conversations
              </h3>
              <div className="space-y-1">
                {conversationPreviews.map((conv) => (
                  <button
                    key={conv.id}
                    className="w-full btn-ghost justify-start gap-3 px-3 py-2.5 rounded-xl text-left transition-all duration-150"
                  >
                    <MessageSquare className="w-5 h-5 text-ui-text-muted flex-shrink-0" />
                    <div className="flex-1 min-w-0 text-left">
                      <p className="text-body-sm font-medium text-ui-text truncate">{conv.title}</p>
                      <div className="flex items-center gap-2 text-micro text-ui-text-subtle mt-0.5">
                        <Clock className="w-3 h-3" />
                        <span>{conv.time}</span>
                        <span>•</span>
                        <span>{conv.messageCount} msgs</span>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </section>
          )}

          {/* Documents Quick Access */}
          {documents.length > 0 && (
            <section>
              <h3 className="text-micro font-mono uppercase tracking-wider text-ui-text-subtle px-2 mb-2">
                Documents ({readyDocs} ready)
              </h3>
              <div className="space-y-1 max-h-60 overflow-y-auto">
                {documents
                  .filter(d => d.processing_status === 'READY')
                  .map((doc) => (
                    <button
                      key={doc.id}
                      className="w-full btn-ghost justify-start gap-3 px-3 py-2 rounded-xl text-left transition-all duration-150"
                    >
                      <FileSpreadsheet className="w-4.5 h-4.5 text-accent-emerald flex-shrink-0" />
                      <div className="flex-1 min-w-0 text-left">
                        <p className="text-body-sm font-medium text-ui-text truncate">{doc.original_filename}</p>
                        <p className="text-micro text-ui-text-subtle mt-0.5">
                          {doc.page_count} pages · {doc.chunk_count} chunks
                        </p>
                      </div>
                    </button>
                  ))}
              </div>
            </section>
          )}

          {/* Empty State */}
          {messages.length === 0 && conversationPreviews.length === 0 && (
            <div className="pt-8 text-center text-ui-text-subtle">
              <p className="text-body-sm">No conversations yet</p>
              <p className="text-caption mt-1">Start a new chat to begin</p>
            </div>
          )}
        </div>
      </aside>
    </>
  );
};