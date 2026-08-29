import React, { useState, useEffect } from 'react';

interface ReadinessGaugeCardProps {
  title?: string;
  status?: 'IDLE' | 'ACTIVE' | 'CONNECTED' | 'DISCONNECTED';
  onAction?: () => void;
}

export const ReadinessGaugeCard: React.FC<ReadinessGaugeCardProps> = ({
  title = 'ReadinessGaugeCard',
  status = 'IDLE',
  onAction,
}) => {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  return (
    <div
      className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-slate-100 shadow-lg hover:border-sky-500/50 transition-all duration-200"
      role="region"
      aria-label={title}
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold tracking-wide uppercase text-sky-400">{title}</h3>
        <span className="px-2 py-0.5 text-xs font-mono rounded bg-sky-950 text-sky-300 border border-sky-800">
          {status}
        </span>
      </div>
      <p className="text-xs text-slate-400 mb-4">Real-time cardiac readiness gauge with dark mode and WCAG 2.1 AA contrast.</p>
      <button
        onClick={onAction}
        className="w-full py-2 px-3 text-xs font-medium rounded-lg bg-sky-600 hover:bg-sky-500 active:bg-sky-700 text-white transition-colors focus:ring-2 focus:ring-sky-400 outline-none"
        aria-label="Execute action"
      >
        Execute Action
      </button>
    </div>
  );
};

export default ReadinessGaugeCard;
