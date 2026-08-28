import React from "react";

export interface SkipToContentProps {
  targetId?: string;
  className?: string;
}

/**
 * Server Component: SkipToContent
 * Renders an accessible skip navigation link targeting the main content landmark.
 */
export function SkipToContent({
  targetId = "main-content",
  className = "",
}: SkipToContentProps) {
  return (
    <a
      href={`#${targetId}`}
      className={`skip-link ${className}`}
    >
      Skip to main content
    </a>
  );
}

export default SkipToContent;
