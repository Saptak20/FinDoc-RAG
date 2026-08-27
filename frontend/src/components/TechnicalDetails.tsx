import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Gauge, CheckCircle2, Zap, Timer, Filter } from 'lucide-react';
import type { ChatMetrics } from '../types/chat';

interface TechnicalDetailsProps {
  metrics: ChatMetrics;
}

const MetricItem: React.FC<{
  icon: React.ReactNode;
  iconBg: string;
  label: string;
  value: React.ReactNode;
  valueColor: string;
}> = ({ icon, iconBg, label, value, valueColor }) => (
  <div className="bg-void-800/40 backdrop-blur-xl rounded-xl p-3 lg:p-4">
    <div className="flex items-center gap-2 mb-1.5">
      <div className={`w-7 h-7 rounded-lg ${iconBg} flex items-center justify-center`}>
        {icon}
      </div>
      <div>
        <p className="text-micro font-mono uppercase tracking-wider text-ui-text-subtle">
          {label}
        </p>
        <p className="font-mono font-bold text-body-sm" style={{ color: valueColor }}>
          {value}
        </p>
      </div>
    </div>
  </div>
);

export const TechnicalDetails: React.FC<TechnicalDetailsProps> = ({ metrics }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="animate-slide-up">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full bg-void-800/40 backdrop-blur-xl rounded-xl p-3 hover:bg-void-800/60 transition-all duration-150 flex items-center justify-between"
      >
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-accent-emerald/10 flex items-center justify-center">
            <Gauge className="w-4 h-4 text-accent-emerald" />
          </div>
          <div className="text-left">
            <p className="text-caption font-medium text-ui-text">Pipeline Telemetry</p>
            <p className="text-micro text-ui-text-subtle">
              {metrics.latency_seconds.toFixed(2)}s total
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          {isOpen ? (
            <ChevronUp className="w-4.5 h-4.5 text-ui-text-subtle" />
          ) : (
            <ChevronDown className="w-4.5 h-4.5 text-ui-text-subtle" />
          )}
        </div>
      </button>

      {isOpen && (
        <div className="mt-2 bg-void-800/30 backdrop-blur-xl rounded-xl p-3 animate-slide-up grid grid-cols-2 lg:grid-cols-4 gap-2">
          <MetricItem
            icon={<Filter className="w-3.5 h-3.5 text-accent-emerald" />}
            iconBg="bg-accent-emerald/10"
            label="Retrieved"
            value={`${metrics.retrieval_candidates} <span className="text-micro font-normal text-ui-text-subtle">chunks</span>`}
            valueColor="var(--color-ui-text)"
          />
          <MetricItem
            icon={<CheckCircle2 className="w-3.5 h-3.5 text-accent-emerald" />}
            iconBg="bg-accent-emerald/10"
            label="Reranked"
            value={`${metrics.reranked_chunks} <span className="text-micro font-normal text-ui-text-subtle">chunks</span>`}
            valueColor="var(--color-accent-emerald)"
          />
          <MetricItem
            icon={<Timer className="w-3.5 h-3.5 text-accent-cyan" />}
            iconBg="bg-accent-cyan/10"
            label="Latency"
            value={`${metrics.latency_seconds.toFixed(2)} <span className="text-micro font-normal text-ui-text-subtle">sec</span>`}
            valueColor="var(--color-accent-cyan)"
          />
          <MetricItem
            icon={<Zap className="w-3.5 h-3.5 text-accent-violet" />}
            iconBg="bg-accent-violet/10"
            label="Grounding"
            value={<span className="inline-flex items-center gap-1 font-medium text-accent-emerald text-caption"><CheckCircle2 className="w-3 h-3" /> Traceable</span>}
            valueColor="var(--color-accent-emerald)"
          />
        </div>
      )}
    </div>
  );
};

export default TechnicalDetails;