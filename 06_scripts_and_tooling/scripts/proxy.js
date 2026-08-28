const net = require('net');
const LOCAL_PORT = 18789;
const REMOTE_HOST = '100.101.39.98';
const REMOTE_PORT = 18789;

net.createServer(function (socket) {
  const client = net.connect(REMOTE_PORT, REMOTE_HOST, function () {
    socket.pipe(client);
    client.pipe(socket);
  });
  socket.on('error', () => {});
  client.on('error', () => {});
}).listen(LOCAL_PORT, () => console.log('Proxy listening on ' + LOCAL_PORT));
