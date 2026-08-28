import React from 'react';
import { PySparkAstCard } from './PySparkAstCard.jsx';
import { TriVaultStatusCard } from './TriVaultStatusCard.jsx';

export function StructuralMetricsTab({ metrics, onDispatchAction }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <PySparkAstCard
        structuralMetrics={metrics}
        onDispatchAction={onDispatchAction}
      />
      <TriVaultStatusCard
        onDispatchAction={onDispatchAction}
      />
    </div>
  );
}

export default StructuralMetricsTab;
