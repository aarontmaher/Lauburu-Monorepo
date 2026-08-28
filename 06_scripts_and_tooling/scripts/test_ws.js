const WebSocket = require('ws');
const ws = new WebSocket('wss://macbook-1.taildb25e9.ts.net?token=mGe5qpmFqnVWbnf1v1y72hWOv0JnQBjoTjo_229F400');
ws.on('open', () => { console.log('Connected!'); process.exit(0); });
ws.on('error', (e) => { console.error('Error:', e.message); process.exit(1); });
