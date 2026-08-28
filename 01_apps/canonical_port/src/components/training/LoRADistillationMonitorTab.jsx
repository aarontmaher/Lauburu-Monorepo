import React from 'react';
import { LoraLossCurveCard } from './LoraLossCurveCard.jsx';
import { TriVaultStatusCard } from './TriVaultStatusCard.jsx';

export function LoRADistillationMonitorTab({ trainingState, onDispatchAction }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <LoraLossCurveCard
        trainingState={trainingState}
        onDispatchAction={onDispatchAction}
      />
      <TriVaultStatusCard
        onDispatchAction={onDispatchAction}
      />
    </div>
  );
}

export default LoRADistillationMonitorTab;
