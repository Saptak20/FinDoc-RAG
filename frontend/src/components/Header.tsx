import React from 'react';
import { Sparkles, RefreshCw, Cpu, Layers, CheckCircle2, AlertTriangle, XCircle, FileSpreadsheet } from 'lucide-react';
import type { SystemStatus } from '../types/chat';

interface HeaderProps {
  status: SystemStatus;
  documentCount: number;
  onOpenSystemInfo: () => void;
  onOpenDocumentLibrary: () => void;
  onRefreshStatus: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  status,
  documentCount,
  onOpenSystemInfo,
  onOpenDocumentLibrary,
  onRefreshStatus,
}) => {
  const getStatusBadge = () => {
    switch (status.status) {
      case 'ready':
        return (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/25 text-emerald-400 text-xs font-medium shadow-glass-subtle transition-all hover:bg-emerald-500/15">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="tracking-tight">System Ready</span>
          </div>
        );
      case 'healthy':
        return (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/25 text-cyan-400 text-xs font-medium shadow-glass-subtle">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span className="tracking-tight">Online</span>
          </div>
        );
      case 'checking':
        return (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/25 text-amber-400 text-xs font-medium shadow-glass-subtle">
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            <span className="tracking-tight">Connecting...</span>
          </div>
        );
      case 'not_ready':
        return (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/25 text-amber-400 text-xs font-medium shadow-glass-subtle">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span className="tracking-tight">Degraded</span>
          </div>
        );
      case 'offline':
      default:
        return (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-rose-500/10 border border-rose-500/25 text-rose-400 text-xs font-medium shadow-glass-subtle">
            <XCircle className="w-3.5 h-3.5" />
            <span className="tracking-tight">Backend Offline</span>
          </div>
        );
    }
  };

  return (
    <header className="sticky top-0 z-30 w-full border-b border-graphite-700/60 bg-graphite-950/80 backdrop-blur-xl transition-colors">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        {/* Left: Brand Identity */}
        <div className="flex items-center gap-3.5">
          <div className="relative group">
            <div className="absolute -inset-0.5 bg-gradient-to-r from-emerald-500 to-cyan-500 rounded-xl blur opacity-30 group-hover:opacity-60 transition duration-300"></div>
            <div className="relative w-9 h-9 rounded-xl bg-graphite-900 border border-graphite-700/80 flex items-center justify-center shadow-glass-subtle">
              <Sparkles className="w-4.5 h-4.5 text-emerald-400" />
            </div>
          </div>

          <div>
            <div className="flex items-center gap-2.5">
              <span className="font-semibold text-base tracking-tight text-white font-sans">
                FinDoc<span className="text-emerald-400 font-mono font-medium">-RAG</span>
              </span>
              <span className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider rounded-md bg-graphite-800 text-slate-300 border border-graphite-700/80">
                <Layers className="w-2.5 h-2.5 text-emerald-400" />
                Hybrid Stack
              </span>
            </div>
            <p className="text-[11px] text-slate-400 hidden md:flex items-center gap-1 font-normal">
              <span>Dynamic Financial Knowledge Ingestion & Grounded QA</span>
            </p>
          </div>
        </div>

        {/* Right: Actions & Live Status */}
        <div className="flex items-center gap-2.5 sm:gap-3">
          <button
            onClick={onRefreshStatus}
            title="Refresh System Health & Readiness"
            className="cursor-pointer transition-transform active:scale-95"
          >
            {getStatusBadge()}
          </button>

          <button
            onClick={onOpenDocumentLibrary}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-300 bg-graphite-850 hover:bg-graphite-800 border border-graphite-700/80 hover:border-emerald-500/40 shadow-glass-subtle hover:text-white transition-all cursor-pointer"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
            <span>Documents</span>
            {documentCount > 0 && (
              <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-graphite-750 text-emerald-300">
                {documentCount}
              </span>
            )}
          </button>

          <button
            onClick={onOpenSystemInfo}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-300 bg-graphite-850 hover:bg-graphite-800 border border-graphite-700/80 hover:border-graphite-600 shadow-glass-subtle hover:text-white transition-all cursor-pointer"
          >
            <Cpu className="w-3.5 h-3.5 text-cyan-400" />
            <span className="hidden sm:inline">Architecture</span>
          </button>
        </div>
      </div>
    </header>
  );
};
