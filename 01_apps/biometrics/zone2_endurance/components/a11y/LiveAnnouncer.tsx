"use client";

import React, { useEffect, useState } from "react";

export interface LiveAnnouncerProps {
  politeMessage?: string;
  assertiveMessage?: string;
  className?: string;
}

/**
 * Accessible ARIA Live Announcer Component
 * 
 * Provides dual screen-reader live regions:
 * 1. Polite Live Region: For non-disruptive announcements (e.g. Zone transitions, milestone pacing)
 * 2. Assertive Live Region: For critical biological alarms (e.g. Lead Off, severe threshold deviations)
 */
export function LiveAnnouncer({
  politeMessage = "",
  assertiveMessage = "",
  className = "sr-only",
}: LiveAnnouncerProps) {
  const [politeText, setPoliteText] = useState(politeMessage);
  const [assertiveText, setAssertiveText] = useState(assertiveMessage);

  useEffect(() => {
    if (politeMessage) {
      setPoliteText(politeMessage);
    }
  }, [politeMessage]);

  useEffect(() => {
    if (assertiveMessage) {
      setAssertiveText(assertiveMessage);
    }
  }, [assertiveMessage]);

  return (
    <div className={className} aria-hidden={false}>
      {/* Polite Live Region for gradual status and zone changes */}
      <div
        id="a11y-polite-announcer"
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        {politeText}
      </div>

      {/* Assertive Live Region for high-priority alerts and lead disconnections */}
      <div
        id="a11y-assertive-announcer"
        role="alert"
        aria-live="assertive"
        aria-atomic="true"
        className="sr-only"
      >
        {assertiveText}
      </div>
    </div>
  );
}

export default LiveAnnouncer;
