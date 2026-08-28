"use client";

import React, { useState } from "react";
import { DfaAlpha1Point, LeadStatus, getZoneMetadata } from "@/types/biometrics";
import { ChevronLeft, ChevronRight, FileSpreadsheet } from "lucide-react";

export interface AccessibleDataTableProps {
  data: DfaAlpha1Point[];
  caption?: string;
  leadStatus?: LeadStatus;
  pageSize?: number;
  className?: string;
}

/**
 * Accessible Data Table Component
 * 
 * Provides an accessible HTML table representation of biometric time-series data
 * for screen-reader users, keyboard navigators, and tabular inspection.
 */
export function AccessibleDataTable({
  data = [],
  caption = "Biometric Telemetry History — DFA alpha-1 and Heart Rate Time Series",
  leadStatus = "CONNECTED",
  pageSize = 10,
  className = "",
}: AccessibleDataTableProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const totalPages = Math.max(1, Math.ceil(data.length / pageSize));
  
  const startIndex = (currentPage - 1) * pageSize;
  const currentRows = data.slice(startIndex, startIndex + pageSize);

  const formatTime = (epochMs: number) => {
    const d = new Date(epochMs);
    return isNaN(d.getTime()) ? "--:--" : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  };

  const handlePrev = () => {
    if (currentPage > 1) setCurrentPage((p) => p - 1);
  };

  const handleNext = () => {
    if (currentPage < totalPages) setCurrentPage((p) => p + 1);
  };

  return (
    <div
      className={`rounded-xl border border-border bg-card p-4 text-card-foreground shadow-sm ${className}`}
      tabIndex={0}
      role="region"
      aria-label="Accessible Biometric Telemetry Data Table"
    >
      <div className="flex flex-wrap items-center justify-between gap-4 pb-3 border-b border-border mb-4">
        <div className="flex items-center gap-2">
          <FileSpreadsheet className="w-5 h-5 text-primary" aria-hidden="true" />
          <h3 className="text-base font-semibold text-foreground">
            Biometric Data Record
          </h3>
        </div>
        <div className="text-xs text-muted-foreground">
          Showing {data.length === 0 ? 0 : startIndex + 1}–{Math.min(startIndex + pageSize, data.length)} of {data.length} records
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm border-collapse">
          <caption className="sr-only">{caption}</caption>
          <thead>
            <tr className="border-b border-border bg-muted/40 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              <th scope="col" className="px-3 py-2.5">Time</th>
              <th scope="col" className="px-3 py-2.5">Heart Rate (BPM)</th>
              <th scope="col" className="px-3 py-2.5">DFA &alpha;1</th>
              <th scope="col" className="px-3 py-2.5">Physiological Zone</th>
              <th scope="col" className="px-3 py-2.5">Kamath Artifact %</th>
              <th scope="col" className="px-3 py-2.5">Power (Watts)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {currentRows.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-muted-foreground italic">
                  {leadStatus === "DISCONNECTED" || leadStatus === "OFF_BODY"
                    ? "Sensor disconnected. No telemetry data recorded."
                    : "Awaiting incoming telemetry samples..."}
                </td>
              </tr>
            ) : (
              currentRows.map((row, index) => {
                const zoneMeta = getZoneMetadata(row.zone);
                return (
                  <tr
                    key={row.timestamp || index}
                    className="hover:bg-muted/30 transition-colors focus-within:bg-muted/40"
                  >
                    <th scope="row" className="px-3 py-2 font-mono text-xs text-foreground font-normal whitespace-nowrap">
                      {formatTime(row.timestamp)}
                    </th>
                    <td className="px-3 py-2 font-mono text-foreground">
                      {row.heartRate > 0 ? row.heartRate : "--"}
                    </td>
                    <td className="px-3 py-2 font-mono font-medium text-foreground">
                      {row.alpha1 ? row.alpha1.toFixed(2) : "--"}
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium"
                        style={{
                          backgroundColor: `${zoneMeta.color}20`,
                          color: zoneMeta.color,
                        }}
                      >
                        <span
                          className="w-1.5 h-1.5 rounded-full"
                          style={{ backgroundColor: zoneMeta.color }}
                          aria-hidden="true"
                        />
                        {zoneMeta.label}
                      </span>
                    </td>
                    <td className="px-3 py-2 font-mono text-xs text-muted-foreground">
                      {typeof row.artifactPercentage === "number" ? `${row.artifactPercentage.toFixed(1)}%` : "--"}
                    </td>
                    <td className="px-3 py-2 font-mono text-xs text-foreground">
                      {row.power ? `${row.power} W` : "--"}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Navigation */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-4 border-t border-border mt-4 text-xs text-muted-foreground">
          <span>
            Page {currentPage} of {totalPages}
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handlePrev}
              disabled={currentPage <= 1}
              aria-label="Previous Page"
              className="inline-flex items-center justify-center p-1.5 rounded-md border border-border bg-card text-foreground hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed min-h-[36px] min-w-[36px] focus-visible:ring-2 focus-visible:ring-primary"
            >
              <ChevronLeft className="w-4 h-4" aria-hidden="true" />
            </button>
            <button
              type="button"
              onClick={handleNext}
              disabled={currentPage >= totalPages}
              aria-label="Next Page"
              className="inline-flex items-center justify-center p-1.5 rounded-md border border-border bg-card text-foreground hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed min-h-[36px] min-w-[36px] focus-visible:ring-2 focus-visible:ring-primary"
            >
              <ChevronRight className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default AccessibleDataTable;
