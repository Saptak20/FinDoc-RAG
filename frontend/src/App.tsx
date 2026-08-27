import { useState, useEffect, useRef } from 'react';
import { TopBar } from './components/TopBar';
import { Sidebar } from './components/Sidebar';
import { ConversationView } from './components/ConversationView';
import { Composer } from './components/Composer';
import { DocumentLibrarySheet } from './components/DocumentLibrarySheet';
import { SystemInfoSheet } from './components/SystemInfoSheet';
import type { Message, SystemStatus, DocumentItem } from './types/chat';
import { sendChatQuery, checkSystemReadiness, fetchDocuments, ApiError } from './services/api';

export function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    status: 'checking',
    application: 'FinDoc-RAG',
  });
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isDocLibraryOpen, setIsDocLibraryOpen] = useState(false);
  const [isSystemInfoOpen, setIsSystemInfoOpen] = useState(false);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedPrompt, setSelectedPrompt] = useState<string>('');

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Poll system readiness and document count
  const fetchStatus = async () => {
    const status = await checkSystemReadiness();
    setSystemStatus(status);
  };

  const refreshDocuments = async () => {
    try {
      const res = await fetchDocuments();
      setDocuments(res.documents);
    } catch {
      // Ignore if offline
    }
  };

  useEffect(() => {
    fetchStatus();
    refreshDocuments();
    const timer = setInterval(() => {
      fetchStatus();
      refreshDocuments();
    }, 20000);
    return () => clearInterval(timer);
  }, []);

  // Auto-scroll when messages change
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSendMessage = async (
    query: string,
    params: { dense_top_k: number; sparse_top_k: number; final_top_k: number }
  ) => {
    if (!query.trim() || isLoading) return;

    const userMessageId = `user-${Date.now()}`;
    const userMessage: Message = {
      id: userMessageId,
      role: 'user',
      content: query.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await sendChatQuery({
        query: query.trim(),
        dense_top_k: params.dense_top_k,
        sparse_top_k: params.sparse_top_k,
        final_top_k: params.final_top_k,
      });

      const assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.answer,
        timestamp: new Date().toISOString(),
        sources: response.sources,
        metrics: response.metrics,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      const errorMessageText =
        err instanceof ApiError
          ? err.message
          : 'Unable to complete request. Please verify your network and that the API server is active.';

      const errorAssistantMessage: Message = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: errorMessageText,
        timestamp: new Date().toISOString(),
        isError: true,
      };

      setMessages((prev) => [...prev, errorAssistantMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearChat = () => {
    if (window.confirm('Clear current conversation history?')) {
      setMessages([]);
    }
  };

  const handleNewChat = () => {
    if (messages.length > 0 && !window.confirm('Start a new conversation? Current history will be cleared.')) {
      return;
    }
    setMessages([]);
    setIsSidebarOpen(false);
  };

  return (
    <div className="min-h-screen bg-void-950 text-ui-text flex">
      {/* Subtle ambient background */}
      <div className="fixed inset-0 bg-mesh-subtle pointer-events-none z-[0]" aria-hidden="true" />
      <div
        className="fixed top-1/4 left-1/2 -translate-x-1/2 w-[500px] h-[300px] bg-accent-emerald/3 blur-[150px] rounded-full pointer-events-none z-[0]"
        aria-hidden="true"
      />

      {/* Sidebar */}
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        onNewChat={handleNewChat}
        messages={messages}
        documents={documents}
      />

      {/* Main content area */}
      <main className="flex-1 flex flex-col min-w-0 relative z-10 lg:pl-0">
        {/* Top Bar */}
        <TopBar
          systemStatus={systemStatus}
          documentCount={documents.length}
          onMenuClick={() => setIsSidebarOpen(true)}
          onDocLibraryClick={() => setIsDocLibraryOpen(true)}
          onSystemInfoClick={() => setIsSystemInfoOpen(true)}
          onRefreshStatus={fetchStatus}
        />

        {/* Conversation workspace */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <ConversationView
            messages={messages}
            isLoading={isLoading}
            messagesEndRef={messagesEndRef}
            onSelectPrompt={setSelectedPrompt}
          />
        </div>

        {/* Composer */}
        <Composer
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
          onClearChat={handleClearChat}
          hasMessages={messages.length > 0}
          initialPrompt={selectedPrompt}
          onPromptUsed={() => setSelectedPrompt('')}
        />
      </main>

      {/* Sheets / Modals */}
      <DocumentLibrarySheet
        isOpen={isDocLibraryOpen}
        onClose={() => setIsDocLibraryOpen(false)}
        onDocumentAdded={refreshDocuments}
        documents={documents}
      />

      <SystemInfoSheet
        isOpen={isSystemInfoOpen}
        onClose={() => setIsSystemInfoOpen(false)}
        status={systemStatus}
      />
    </div>
  );
}

export default App;