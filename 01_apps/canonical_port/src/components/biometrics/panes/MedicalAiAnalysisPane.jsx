import React, { useState, useEffect, useRef } from 'react';
import { api } from '../../../services/api';

export function MedicalAiAnalysisPane() {
  const [aiModel, setAiModel] = useState("medgemma");
  const [aiAnalysis, setAiAnalysis] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isContinuous, setIsContinuous] = useState(false);
  
  const windowTimerRef = useRef(null);

  const runAnalysisCycle = async () => {
    setIsAnalyzing(true);
    setAiAnalysis(prev => prev + `\n[${new Date().toLocaleTimeString()}] Extracting sliding 30s window... Running inference on ${aiModel}...`);
    try {
      const resp = await api.post("/biometrics/movesense/analyze", {
        model_id: aiModel,
        prompt: "Analyze the sliding 30-60s window of ECG telemetry for arrhythmias, heart rate variability, and clinical insights:"
      });
      setAiAnalysis(prev => prev + `\n[${new Date().toLocaleTimeString()}] Result: ` + (resp.analysis || resp.error || JSON.stringify(resp)));
    } catch (err) {
      setAiAnalysis(prev => prev + `\n[${new Date().toLocaleTimeString()}] Error: ` + err.message);
    } finally {
      setIsAnalyzing(false);
    }
  };

  useEffect(() => {
    if (isContinuous) {
      runAnalysisCycle();
      windowTimerRef.current = setInterval(runAnalysisCycle, 30000); // 30s sliding window
    } else {
      if (windowTimerRef.current) clearInterval(windowTimerRef.current);
    }
    return () => {
      if (windowTimerRef.current) clearInterval(windowTimerRef.current);
    };
  }, [isContinuous, aiModel]);

  return (
    <div className="cyber-card" style={{ gridColumn: '1 / -1' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ fontWeight: 600, color: 'var(--accent-purple)' }}>HEAVY MEDICAL AI (30-60s SLIDING WINDOW)</div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            <input 
              type="checkbox" 
              checked={isContinuous} 
              onChange={e => setIsContinuous(e.target.checked)} 
              style={{ marginRight: '6px' }}
            />
            Continuous Window
          </label>
          <select 
            value={aiModel} 
            onChange={(e) => setAiModel(e.target.value)}
            style={{ background: 'var(--bg-card)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', padding: '4px 8px' }}
          >
            <option value="medgemma">MedGemma-4B-ECG (Specialized)</option>
            <option value="meditron">Meditron-7B</option>
            <option value="biomistral">BioMistral-7B</option>
          </select>
          <button 
            className="cyber-btn" 
            onClick={runAnalysisCycle}
            disabled={isAnalyzing}
          >
            {isAnalyzing ? 'Analyzing...' : 'Force 30s Window'}
          </button>
        </div>
      </div>
      <div style={{ background: 'var(--bg-dark)', padding: '12px', borderRadius: '4px', minHeight: '120px', maxHeight: '200px', overflowY: 'auto', whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.85rem' }}>
        {aiAnalysis || "Select a medical LLM and enable Continuous Window to evaluate the live ECG stream in the background without blocking the React UI thread (TinyML runs real-time)."}
      </div>
    </div>
  );
}
