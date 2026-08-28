"use client";

import { useEffect, useState, useRef } from "react";
import { Activity } from "lucide-react";

export function EcgChart() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isAnimating, setIsAnimating] = useState(true);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !isAnimating) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let offset = 0;

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.beginPath();
      ctx.strokeStyle = "#ef4444"; // red-500
      ctx.lineWidth = 2;
      ctx.lineJoin = "round";

      const height = canvas.height;
      const width = canvas.width;
      const midY = height / 2;

      for (let x = 0; x < width; x++) {
        // Simple mock ECG pattern
        const t = (x + offset) * 0.05;
        let y = midY;
        
        // Add periodic spikes
        if (Math.sin(t) > 0.95) {
          y -= 40 * Math.sin((t - Math.PI / 2) * 10);
        } else {
          // Small noise
          y += Math.sin(t * 5) * 2;
        }

        if (x === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.stroke();

      offset += 2;
      animationFrameId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [isAnimating]);

  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 shadow-sm h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold flex items-center gap-2 text-gray-900 dark:text-gray-100">
          <Activity className="h-5 w-5 text-red-500" aria-hidden="true" />
          Live ECG
        </h3>
        <button
          onClick={() => setIsAnimating(!isAnimating)}
          className="text-xs font-medium px-2 py-1 rounded-md bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors focus:outline-none focus:ring-2 focus:ring-red-500"
          aria-label={isAnimating ? "Pause ECG animation" : "Play ECG animation"}
        >
          {isAnimating ? "Pause" : "Play"}
        </button>
      </div>
      
      <div 
        className="flex-1 min-h-[200px] w-full bg-gray-50 dark:bg-black/50 rounded-lg overflow-hidden relative"
        role="img"
        aria-label="Live Electrocardiogram (ECG) data visualization showing heart electrical activity over time"
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
          Real-time ECG visualization. Current heart rate is stable at approximately 65 BPM with normal sinus rhythm.
        </div>
      </div>
    </div>
  );
}
