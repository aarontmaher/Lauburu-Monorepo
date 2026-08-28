"use client";

import { useEffect, useState, useRef } from "react";
import { TrendingUp } from "lucide-react";

export function DfaChart() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [data, setData] = useState<number[]>([]);

  // Generate some mock DFA-alpha1 data points
  useEffect(() => {
    const initialData = Array.from({ length: 20 }, (_, i) => {
      // Start around 1.2, drift down towards 0.75 (Zone 2 boundary)
      const base = 1.2 - (i * 0.02);
      const noise = (Math.random() - 0.5) * 0.1;
      return Math.max(0.4, Math.min(1.5, base + noise));
    });
    setData(initialData);

    const interval = setInterval(() => {
      setData(prev => {
        const last = prev[prev.length - 1];
        // Random walk with tendency to stay near 0.75
        const pull = (0.75 - last) * 0.1;
        const noise = (Math.random() - 0.5) * 0.08;
        const next = Math.max(0.4, Math.min(1.5, last + pull + noise));
        return [...prev.slice(1), next];
      });
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  // Draw chart
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || data.length === 0) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    const height = canvas.height;
    const width = canvas.width;
    const padding = 20;
    
    const drawAreaWidth = width - padding * 2;
    const drawAreaHeight = height - padding * 2;
    
    // Y-axis scales from 0.4 to 1.5
    const minY = 0.4;
    const maxY = 1.5;
    
    const getY = (val: number) => {
      const normalized = (val - minY) / (maxY - minY);
      return height - padding - (normalized * drawAreaHeight);
    };

    const getX = (index: number) => {
      return padding + (index / (data.length - 1)) * drawAreaWidth;
    };

    // Draw Zone 2 boundary line (0.75)
    ctx.beginPath();
    ctx.strokeStyle = "rgba(59, 130, 246, 0.5)"; // blue-500
    ctx.setLineDash([5, 5]);
    ctx.lineWidth = 1;
    const boundaryY = getY(0.75);
    ctx.moveTo(padding, boundaryY);
    ctx.lineTo(width - padding, boundaryY);
    ctx.stroke();
    ctx.setLineDash([]);
    
    // Boundary text
    ctx.fillStyle = "rgba(59, 130, 246, 0.8)";
    ctx.font = "12px sans-serif";
    ctx.fillText("0.75 Threshold", padding, boundaryY - 5);

    // Draw data line
    ctx.beginPath();
    ctx.strokeStyle = "#10b981"; // emerald-500
    ctx.lineWidth = 3;
    ctx.lineJoin = "round";

    data.forEach((val, i) => {
      if (i === 0) ctx.moveTo(getX(i), getY(val));
      else ctx.lineTo(getX(i), getY(val));
    });
    
    ctx.stroke();

    // Draw points
    ctx.fillStyle = "#ffffff";
    data.forEach((val, i) => {
      ctx.beginPath();
      ctx.arc(getX(i), getY(val), 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    });

  }, [data]);

  const latestValue = data.length > 0 ? data[data.length - 1].toFixed(2) : "0.00";

  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 shadow-sm h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold flex items-center gap-2 text-gray-900 dark:text-gray-100">
          <TrendingUp className="h-5 w-5 text-emerald-500" aria-hidden="true" />
          DFA-a1 (Fatigue)
        </h3>
        <div className="text-2xl font-bold font-mono text-gray-800 dark:text-gray-100" aria-live="polite" aria-atomic="true">
          <span className="sr-only">Current DFA-alpha1 value:</span>
          {latestValue}
        </div>
      </div>
      
      <div 
        className="flex-1 min-h-[200px] w-full bg-gray-50 dark:bg-black/50 rounded-lg overflow-hidden relative"
        role="img"
        aria-label="Line chart showing DFA-alpha1 metric over time. Values near 0.75 indicate aerobic threshold (Zone 2)."
      >
        <canvas 
          ref={canvasRef} 
          width={800} 
          height={300} 
          className="w-full h-full object-fill"
          aria-hidden="true"
        />
        
        {/* Screen reader only fallback description */}
        <div className="sr-only">
          The chart tracks DFA-alpha1 values to monitor aerobic fatigue. The current value is {latestValue}. Values above 0.75 indicate lower fatigue intensity, while dropping below 0.75 suggests transition beyond aerobic threshold.
        </div>
      </div>
    </div>
  );
}
