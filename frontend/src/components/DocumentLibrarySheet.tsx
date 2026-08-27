import React, { useState, useEffect, useRef } from 'react';
import {
  X,
  Upload,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Layers,
  FileSpreadsheet,
  AlertTriangle,
  Clock,
  FileText,
} from 'lucide-react';
import type { DocumentItem } from '../types/chat';
import { fetchDocuments, uploadDocument, deleteDocument, ApiError } from '../services/api';
import DocumentItemRow from './DocumentItemRow';

interface DocumentLibrarySheetProps {
  isOpen: boolean;
  onClose: () => void;
  onDocumentAdded?: () => void;
  documents: DocumentItem[];
}

export const DocumentLibrarySheet: React.FC<DocumentLibrarySheetProps> = ({
  isOpen,
  onClose,
  onDocumentAdded,
  documents: initialDocuments,
}) => {
  const [documents, setDocuments] = useState<DocumentItem[]>(initialDocuments);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [expandedDocId, setExpandedDocId] = useState<number | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const sheetRef = useRef<HTMLDivElement>(null);

  const loadDocuments = async () => {
    try {
      setIsLoading(true);
      const res = await fetchDocuments();
      setDocuments(res.documents);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to load documents.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadDocuments();
      setErrorMessage(null);
      setSuccessMessage(null);
    }
  }, [isOpen]);

  // Poll when any document is in PENDING or PROCESSING status
  useEffect(() => {
    let timer: ReturnType<typeof setInterval>;
    const hasActiveProcessing = documents.some(
      (d) => d.processing_status === 'PROCESSING' || d.processing_status === 'PENDING'
    );

    if (isOpen && hasActiveProcessing) {
      timer = setInterval(async () => {
        try {
          const res = await fetchDocuments();
          setDocuments(res.documents);
          if (onDocumentAdded) onDocumentAdded();
        } catch {
          // Silent polling fail
        }
      }, 3000);
    }

    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isOpen, documents, onDocumentAdded]);

  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setErrorMessage('Please select a valid PDF document (.pdf).');
      return;
    }

    try {
      setIsUploading(true);
      setErrorMessage(null);
      setSuccessMessage(null);

      const res = await uploadDocument(file);
      setSuccessMessage(res.message);
      await loadDocuments();
      if (onDocumentAdded) onDocumentAdded();
    } catch (err: any) {
      const msg = err instanceof ApiError ? err.message : 'Error uploading file.';
      setErrorMessage(msg);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDelete = async (docId: number, docName: string) => {
    if (!window.confirm(`Are you sure you want to delete '${docName}'? This will purge its chunks from retrieval indexes.`)) {
      return;
    }

    try {
      setErrorMessage(null);
      await deleteDocument(docId);
      setSuccessMessage(`Document '${docName}' removed successfully.`);
      await loadDocuments();
      if (onDocumentAdded) onDocumentAdded();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to delete document.');
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'READY':
        return { label: 'Ready', icon: CheckCircle2, className: 'badge-success' };
      case 'PROCESSING':
        return { label: 'Indexing…', icon: Loader2, className: 'badge-warning animate-pulse-subtle' };
      case 'PENDING':
        return { label: 'Queued', icon: Clock, className: 'badge-neutral animate-pulse-subtle' };
      case 'FAILED':
        return { label: 'Failed', icon: AlertTriangle, className: 'badge-error' };
      default:
        return { label: status, icon: FileText, className: 'badge-neutral' };
    }
  };

  if (!isOpen) return null;

  const totalPages = documents.reduce((acc, d) => acc + (d.page_count || 0), 0);
  const totalChunks = documents.reduce((acc, d) => acc + (d.chunk_count || 0), 0);
  const readyCount = documents.filter((d) => d.processing_status === 'READY').length;

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
        ref={sheetRef}
        className="fixed inset-y-0 right-0 z-[400] w-full max-w-2xl lg:max-w-3xl bg-void-900 border-l border-void-700 shadow-glass-3 animate-slide-in-right flex flex-col overflow-hidden"
        role="dialog"
        aria-modal="true"
        aria-labelledby="doc-library-title"
      >
        {/* Header */}
        <div className="flex items-center justify-between h-12 px-4 lg:px-5 border-b border-void-700">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-accent-emerald/10 flex items-center justify-center">
              <FileSpreadsheet className="w-4.5 h-4.5 text-accent-emerald" />
            </div>
            <div>
              <h2 id="doc-library-title" className="font-display font-semibold text-body-sm tracking-tight text-ui-text">
                Document Library
              </h2>
              <p className="text-micro text-ui-text-subtle">
                {readyCount}/{documents.length} indexed · {totalPages.toLocaleString()} pages · {totalChunks.toLocaleString()} chunks
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="btn-icon"
            aria-label="Close document library"
          >
            <X className="w-4.5 h-4.5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 lg:p-5 space-y-4">
          {/* Status Alerts */}
          {errorMessage && (
            <div className="bg-void-800/60 backdrop-blur-xl rounded-xl p-3 border border-accent-rose/20 animate-fade-in flex items-start gap-2.5">
              <AlertCircle className="w-4.5 h-4.5 text-accent-rose flex-shrink-0 mt-0.5" />
              <p className="text-body-sm text-accent-rose">{errorMessage}</p>
            </div>
          )}

          {successMessage && (
            <div className="bg-void-800/60 backdrop-blur-xl rounded-xl p-3 border border-accent-emerald/20 animate-fade-in flex items-start gap-2.5">
              <CheckCircle2 className="w-4.5 h-4.5 text-accent-emerald flex-shrink-0 mt-0.5" />
              <p className="text-body-sm text-accent-emerald">{successMessage}</p>
            </div>
          )}

          {/* Upload Zone - Compact */}
          <div
            onClick={() => fileInputRef.current?.click()}
            className={`bg-void-800/40 hover:bg-void-800/60 backdrop-blur-xl rounded-xl p-5 lg:p-6 text-center transition-all duration-150 border-2 ${
              isUploading
                ? 'border-accent-emerald/30 bg-accent-emerald/3'
                : 'border-void-700/40 hover:border-accent-emerald/30'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleFileChange}
              disabled={isUploading}
              className="hidden"
            />
            <div className="flex flex-col items-center justify-center gap-2.5">
              {isUploading ? (
                <>
                  <Loader2 className="w-7 h-7 text-accent-emerald animate-spin mx-auto" />
                  <p className="text-body font-medium text-accent-emerald">
                    Uploading & initiating background ingestion…
                  </p>
                  <p className="text-caption text-ui-text-subtle">This may take a moment for large documents</p>
                </>
              ) : (
                <>
                  <div className="w-12 h-12 rounded-xl bg-void-900/50 border border-void-700/50 flex items-center justify-center mx-auto group-hover:bg-accent-emerald/10 group-hover:border-accent-emerald/20 transition-all duration-150">
                    <Upload className="w-5 h-5 text-accent-emerald" />
                  </div>
                  <div>
                    <p className="text-body font-semibold text-ui-text">
                      Add Financial Document
                    </p>
                    <p className="text-caption text-ui-text-subtle mt-0.5">
                      PDF format · Max 50 MB · Automatic text extraction & FAISS/BM25 indexing
                    </p>
                  </div>
                  <p className="text-micro font-mono text-ui-text-subtle/60">
                    Click or drag & drop
                  </p>
                </>
              )}
            </div>
          </div>

          {/* Documents List */}
          <section>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-micro font-mono uppercase tracking-wider text-ui-text-subtle">
                Documents ({documents.length})
              </h3>
              <span className="text-micro font-mono text-ui-text-subtle">
                {readyCount} ready
              </span>
            </div>

            {isLoading && documents.length === 0 && (
              <div className="bg-void-800/40 rounded-xl p-6 text-center animate-fade-in">
                <Loader2 className="w-5 h-5 text-accent-emerald animate-spin mx-auto mb-2" />
                <p className="text-body-sm text-ui-text-muted">Loading documents…</p>
              </div>
            )}

            {!isLoading && documents.length === 0 && (
              <div className="bg-void-800/40 rounded-xl p-6 text-center">
                <FileText className="w-10 h-10 text-void-700 mx-auto mb-2" />
                <p className="text-body-sm text-ui-text-muted">No documents yet</p>
                <p className="text-caption text-ui-text-subtle mt-0.5">Upload your first PDF to begin</p>
              </div>
            )}

            {!isLoading && documents.length > 0 && (
              <div className="space-y-1.5">
                {documents.map((doc) => (
                  <DocumentItemRow
                    key={doc.id}
                    doc={doc}
                    isExpanded={expandedDocId === doc.id}
                    onToggle={() => setExpandedDocId(expandedDocId === doc.id ? null : doc.id)}
                    onDelete={() => handleDelete(doc.id, doc.original_filename)}
                    formatFileSize={formatFileSize}
                    getStatusConfig={getStatusConfig}
                  />
                ))}
              </div>
            )}
          </section>

          {/* Footer */}
          <div className="pt-3 border-t border-void-700/30 flex items-center justify-between text-micro text-ui-text-subtle">
            <div className="flex items-center gap-1 text-accent-emerald">
              <Layers className="w-3 h-3" />
              <span>Incremental index updates with deterministic chunk IDs</span>
            </div>
            <button
              onClick={onClose}
              className="btn-primary px-3 py-1.5 text-caption"
            >
              Done
            </button>
          </div>
        </div>
      </div>
    </>
  );
};