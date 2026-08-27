import React from 'react';
import { FileText, ChevronDown, AlertTriangle, Trash2 } from 'lucide-react';
import type { DocumentItem } from '../types/chat';

interface DocumentItemProps {
  doc: DocumentItem;
  isExpanded: boolean;
  onToggle: () => void;
  onDelete: () => void;
  formatFileSize: (bytes: number) => string;
  getStatusConfig: (status: string) => { label: string; icon: React.ComponentType<{ className?: string }>; className: string };
}

const DocumentItemRow: React.FC<DocumentItemProps> = ({
  doc,
  isExpanded,
  onToggle,
  onDelete,
  formatFileSize,
  getStatusConfig,
}) => {
  const statusConfig = getStatusConfig(doc.processing_status);
  const StatusIcon = statusConfig.icon;

  return (
    <div
      className={`bg-void-800/30 hover:bg-void-800/50 rounded-xl overflow-hidden transition-all duration-150 border border-void-700/40 ${
        isExpanded ? 'bg-void-800/60 border-accent-emerald/20' : ''
      }`}
    >
      {/* Main Row */}
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2.5 p-3 lg:p-4 text-left"
      >
        <div className="w-9 h-9 rounded-lg bg-void-900/50 border border-void-700/50 flex items-center justify-center flex-shrink-0">
          <FileText className="w-4.5 h-4.5 text-accent-emerald" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-medium text-body text-ui-text truncate" title={doc.original_filename}>
            {doc.original_filename}
          </p>
          <div className="flex items-center gap-1.5 text-micro text-ui-text-subtle mt-0.5">
            <span>{formatFileSize(doc.file_size_bytes)}</span>
            <span>•</span>
            <span>{doc.page_count > 0 ? `${doc.page_count} pages` : 'Extracting…'}</span>
            <span>•</span>
            <span>{doc.chunk_count > 0 ? `${doc.chunk_count} chunks` : 'Pending chunks'}</span>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className={`${statusConfig.className} flex items-center gap-1`}>
            <StatusIcon className="w-2.5 h-2.5" />
            {statusConfig.label}
          </span>
          <ChevronDown className={`w-4 h-4 text-ui-text-subtle transition-transform duration-150 ${isExpanded ? 'rotate-180' : ''}`} />
        </div>
      </button>

      {/* Expanded Details */}
      <div className="border-t border-void-700/30 px-4 lg:px-5 pb-3 animate-slide-up">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-caption">
          <div className="bg-void-900/40 rounded-lg p-2">
            <p className="text-ui-text-subtle mb-0.5">Created</p>
            <p className="font-mono text-body-sm text-ui-text">
              {new Date(doc.created_at).toLocaleString()}
            </p>
          </div>
          <div className="bg-void-900/40 rounded-lg p-2">
            <p className="text-ui-text-subtle mb-0.5">Updated</p>
            <p className="font-mono text-body-sm text-ui-text">
              {new Date(doc.updated_at).toLocaleString()}
            </p>
          </div>
          <div className="bg-void-900/40 rounded-lg p-2">
            <p className="text-ui-text-subtle mb-0.5">Pages</p>
            <p className="font-mono font-bold text-body text-accent-cyan">{doc.page_count}</p>
          </div>
          <div className="bg-void-900/40 rounded-lg p-2">
            <p className="text-ui-text-subtle mb-0.5">Chunks</p>
            <p className="font-mono font-bold text-body text-accent-emerald">{doc.chunk_count}</p>
          </div>
          <div className="bg-void-900/40 rounded-lg p-2 sm:col-span-2">
            <p className="text-ui-text-subtle mb-0.5">Stored Filename</p>
            <p className="font-mono text-body-sm text-ui-text break-all">{doc.filename}</p>
          </div>
          {doc.processing_error && (
            <div className="bg-void-900/40 rounded-lg p-2 sm:col-span-2 border border-accent-rose/20 bg-accent-rose/3">
              <p className="text-ui-text-subtle mb-0.5 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3 text-accent-rose" />
                Error
              </p>
              <p className="font-mono text-body-sm text-accent-rose break-all">{doc.processing_error}</p>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-2 mt-3 pt-2 border-t border-void-700/30">
          <button
            className="btn-secondary px-3 py-1.5 text-caption"
            onClick={onDelete}
            disabled={doc.processing_status === 'PROCESSING'}
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Delete Document</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default DocumentItemRow;