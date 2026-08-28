import React from 'react';

export function ToolingCommerceView({ toolingState, onDispatchAction }) {
  const mcpServers = toolingState?.mcpServers || [];
  const skills = toolingState?.skillsCatalog || [];
  const shopify = toolingState?.shopifyCommerce || {};

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header Banner */}
      <div className="cyber-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '1.4rem' }}>🧰</span>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              6. TOOLING, SKILLS & SHOPIFY COMMERCE
            </h2>
            <span className="badge badge-amber">12 MCP / 13 SKILLS</span>
          </div>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            12 Model Context Protocol (MCP) Servers, Spec-00 to Spec-12 Skills Catalog, and Headless Shopify Commerce.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="cyber-btn" onClick={() => onDispatchAction && onDispatchAction('/audit')}>
            🔍 Audit 12 MCPs
          </button>
          <button className="cyber-btn" onClick={() => onDispatchAction && onDispatchAction('/cron')}>
            🛍️ Sync Shopify
          </button>
        </div>
      </div>

      {/* Shopify Banner */}
      <div className="cyber-card" style={{ borderLeft: '3px solid var(--accent-amber)' }}>
        <div style={{ fontWeight: 600, color: 'var(--accent-amber)', marginBottom: '8px' }}>
          SHOPIFY STOREFRONT GRAPHQL & MEMBERSHIP COMMERCE
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', fontSize: '0.8rem' }}>
          <div>
            <div style={{ color: 'var(--text-muted)' }}>Storefront URL</div>
            <div style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>{shopify.storefrontUrl || 'https://shop.lauburu.ai'}</div>
          </div>
          <div>
            <div style={{ color: 'var(--text-muted)' }}>Membership Tier</div>
            <div style={{ color: 'var(--text-primary)' }}>{shopify.subscriptionTier || 'Titanium All-Access'}</div>
          </div>
          <div>
            <div style={{ color: 'var(--text-muted)' }}>Active Memberships</div>
            <div style={{ color: 'var(--accent-emerald)', fontWeight: 600 }}>{shopify.activeMemberships || 1420} Subscribers</div>
          </div>
          <div>
            <div style={{ color: 'var(--text-muted)' }}>Catalog Sync</div>
            <div style={{ color: 'var(--accent-emerald)' }}>● SYNCED (GraphQL 2026-01)</div>
          </div>
        </div>
      </div>

      {/* MCP Servers Grid */}
      <div className="cyber-card" style={{ padding: '0', overflow: 'hidden' }}>
        <div style={{ padding: '16px', borderBottom: '1px solid var(--border-subtle)', fontWeight: 600, color: 'var(--text-primary)' }}>
          12 MODEL CONTEXT PROTOCOL (MCP) SERVERS REGISTRY
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', textAlign: 'left' }}>
            <thead>
              <tr style={{ background: 'var(--bg-tertiary)', borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
                <th style={{ padding: '10px 14px' }}>Server Name</th>
                <th style={{ padding: '10px 14px' }}>Tools Count</th>
                <th style={{ padding: '10px 14px' }}>Description & Scope</th>
                <th style={{ padding: '10px 14px' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {mcpServers.map((s, i) => (
                <tr key={i} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                  <td style={{ padding: '10px 14px', fontWeight: 600, color: 'var(--accent-cyan)' }}>{s.name}</td>
                  <td style={{ padding: '10px 14px' }}>{s.toolCount} tools</td>
                  <td style={{ padding: '10px 14px', color: 'var(--text-secondary)' }}>{s.description}</td>
                  <td style={{ padding: '10px 14px' }}>
                    <span className="badge badge-emerald">● {s.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Skills Catalog */}
      <div className="cyber-card">
        <div style={{ fontWeight: 600, color: 'var(--accent-cyan)', marginBottom: '12px' }}>
          SPEC-00 THROUGH SPEC-12 AGENT SKILLS CATALOG
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '10px' }}>
          {skills.map((sk, i) => (
            <div key={i} style={{ padding: '8px 12px', background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-primary)' }}>{sk.name}</div>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>{sk.domain}</div>
              </div>
              <span className="badge badge-emerald">● ACTIVE</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default ToolingCommerceView;
