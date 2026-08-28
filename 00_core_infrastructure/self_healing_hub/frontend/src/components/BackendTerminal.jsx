import React, { useEffect, useRef } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';

export default function BackendTerminal({ title, endpoint }) {
  const terminalRef = useRef(null);
  const xtermRef = useRef(null);
  const fitAddonRef = useRef(null);

  useEffect(() => {
    if (!terminalRef.current) return;

    xtermRef.current = new Terminal({
      theme: { background: '#000000', foreground: '#00ff00' },
      fontSize: 11,
      fontFamily: 'monospace',
      disableStdin: true,
      cursorBlink: false
    });

    fitAddonRef.current = new FitAddon();
    xtermRef.current.loadAddon(fitAddonRef.current);
    xtermRef.current.open(terminalRef.current);
    fitAddonRef.current.fit();

    xtermRef.current.writeln(`\x1b[33mConnecting to ${title} Daemon...\x1b[0m`);

    const apiHost = window.location.hostname || 'localhost';
    const evtSource = new EventSource(`http://${apiHost}:5001${endpoint}`);

    evtSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.line) {
          xtermRef.current.writeln(data.line);
        }
      } catch (e) {
        xtermRef.current.writeln(event.data);
      }
    };

    evtSource.onerror = () => {
      xtermRef.current.writeln(`\x1b[31m[Disconnected from ${title} Daemon]\x1b[0m`);
    };

    const resizeObserver = new ResizeObserver(() => {
      if (fitAddonRef.current) {
        fitAddonRef.current.fit();
      }
    });
    resizeObserver.observe(terminalRef.current);

    return () => {
      evtSource.close();
      resizeObserver.disconnect();
      xtermRef.current?.dispose();
    };
  }, [title, endpoint]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', border: '1px solid #444', borderRadius: '4px', overflow: 'hidden' }}>
      <div style={{ background: '#333', color: '#fff', fontSize: '11px', padding: '4px 8px', fontWeight: 'bold' }}>
        {title}
      </div>
      <div ref={terminalRef} style={{ flex: 1, background: '#000', overflow: 'hidden' }} />
    </div>
  );
}
