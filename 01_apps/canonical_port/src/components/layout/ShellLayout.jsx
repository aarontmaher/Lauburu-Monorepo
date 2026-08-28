import React from 'react';
import { HeaderStatusBar } from './HeaderStatusBar.jsx';
import { SidebarNav } from './SidebarNav.jsx';
import { SlashCommandDock } from '../terminal/SlashCommandDock.jsx';

export function ShellLayout({
  activeRoute,
  setActiveRoute,
  isSidebarCollapsed,
  toggleSidebar,
  clusterVram,
  networkMetrics,
  isConnected = true,
  onDispatchAction,
  actionNotification,
  activeEngine = 'auto',
  onCycleEngine,
  selectedNodeId,
  onSelectNode,
  children
}) {
  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <SidebarNav
        activeRoute={activeRoute}
        setActiveRoute={setActiveRoute}
        isSidebarCollapsed={isSidebarCollapsed}
        toggleSidebar={toggleSidebar}
      />

      {/* Main Content Area */}
      <div className="main-content-area">
        {/* Master Persistent Top Header (Promoted from Track Alpha) */}
        <HeaderStatusBar
          activeRoute={activeRoute}
          clusterVram={clusterVram}
          networkMetrics={networkMetrics}
          isConnected={isConnected}
          onDispatchAction={onDispatchAction}
          selectedNodeId={selectedNodeId}
          onSelectNode={onSelectNode}
        />

        {/* Action Notification Banner */}
        {actionNotification && (
          <div style={{
            background: 'rgba(0, 255, 204, 0.15)',
            borderBottom: '1px solid var(--accent-cyan)',
            color: 'var(--accent-cyan)',
            padding: '8px 20px',
            fontSize: '0.8rem',
            fontFamily: 'var(--font-mono)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            animation: 'fadeIn 0.2s ease-in-out',
            zIndex: 15
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>⚡ [ACTION DISPATCHED]</span>
              <span>{actionNotification.summary}</span>
            </div>
            <span style={{ color: 'var(--text-muted)' }}>{actionNotification.timestamp}</span>
          </div>
        )}

        {/* Viewport */}
        <main className="content-viewport" style={{ flex: 1, overflowY: 'auto' }}>
          {children}
        </main>

        {/* Persistent Bottom Dock (Track Beta SlashCommandDock) */}
        <footer style={{
          borderTop: '1px solid var(--border-subtle)',
          background: 'var(--bg-secondary)',
          zIndex: 10
        }}>
          <SlashCommandDock
            onDispatchAction={onDispatchAction}
            activeEngine={activeEngine}
            onCycleEngine={onCycleEngine}
          />
        </footer>
      </div>
    </div>
  );
}

export default ShellLayout;
