const net = require('net');
const LOCAL_PORT = 18789;
const REMOTE_HOST = '100.101.39.98';
const REMOTE_PORT = 18789;

net.createServer(function (socket) {
  console.log('Received connection');
  const client = net.connect(REMOTE_PORT, REMOTE_HOST, function () {
    console.log('Connected to remote');
    socket.pipe(client);
    client.pipe(socket);
  });
  socket.on('error', (e) => console.log('Socket error: ' + e));
  client.on('error', (e) => console.log('Client error: ' + e));
}).listen(LOCAL_PORT, () => console.log('Proxy2 listening on ' + LOCAL_PORT));
