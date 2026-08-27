import React from 'react';
import { Menu, Cpu, FileSpreadsheet } from 'lucide-react';
import type { SystemStatus } from '../types/chat';

interface TopBarProps {
  systemStatus: SystemStatus;
  documentCount: number;
  onMenuClick: () => void;
  onDocLibraryClick: () => void;
  onSystemInfoClick: () => void;
  onRefreshStatus: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({
  systemStatus,
  documentCount,
  onMenuClick,
  onDocLibraryClick,
  onSystemInfoClick,
  onRefreshStatus,
}) => {
  const getStatusConfig = () => {
    switch (systemStatus.status) {
      case 'ready':
        return { label: 'Ready', className: 'status-ready', dotClass: '' };
      case 'healthy':
        return { label: 'Online', className: 'status-healthy', dotClass: '' };
      case 'checking':
        return { label: 'Connecting…', className: 'status-checking', dotClass: '' };
      case 'not_ready':
        return { label: 'Degraded', className: 'status-degraded', dotClass: '' };
      case 'offline':
      default:
        return { label: 'Offline', className: 'status-offline', dotClass: '' };
    }
  };

  const status = getStatusConfig();

  return (
    <header className="sticky top-0 z-[200] w-full border-b border-void-700 bg-void-900/80 backdrop-blur-xl transition-colors">
      <div className="container-main h-12 flex items-center justify-between gap-4">
        {/* Left: Brand + Menu */}
        <div className="flex items-center gap-3">
          <button
            onClick={onMenuClick}
            className="btn-icon -ml-1 lg:hidden"
            aria-label="Open navigation"
          >
            <Menu className="w-5 h-5" />
          </button>

          <div className="flex items-center gap-2.5">
            <span className="font-display font-semibold text-body tracking-tight text-ui-text">
              FinDoc<span className="text-accent-emerald font-mono font-medium">-RAG</span>
            </span>
            <span className="hidden lg:inline-flex items-center gap-1 px-2 py-0.5 text-micro font-mono uppercase tracking-wider rounded-md bg-void-800/50 text-ui-text-subtle border border-void-700/30">
              <FileSpreadsheet className="w-3 h-3 text-accent-emerald" />
              {documentCount} {documentCount === 1 ? 'Document' : 'Documents'}
            </span>
          </div>
        </div>

        {/* Right: Status + Actions */}
        <div className="flex items-center gap-2">
          {/* System Status Indicator */}
          <button
            onClick={onRefreshStatus}
            title="Refresh system status"
            className="btn-ghost gap-2 px-3 py-1.5"
          >
            <span className={`status-dot ${status.className}`} aria-hidden="true" />
            <span className="hidden sm:inline text-caption font-medium text-ui-text-muted">{status.label}</span>
          </button>

          {/* Document Library */}
          <button
            onClick={onDocLibraryClick}
            className="btn-icon lg:btn-secondary lg:px-3 lg:py-1.5"
            aria-label="Document library"
          >
            <FileSpreadsheet className="w-4.5 h-4.5 text-accent-emerald" />
            <span className="hidden lg:inline">Library</span>
          </button>

          {/* System Info */}
          <button
            onClick={onSystemInfoClick}
            className="btn-icon lg:btn-secondary lg:px-3 lg:py-1.5"
            aria-label="System architecture"
          >
            <Cpu className="w-4.5 h-4.5 text-accent-cyan" />
            <span className="hidden lg:inline">Architecture</span>
          </button>
        </div>
      </div>
    </header>
  );
};