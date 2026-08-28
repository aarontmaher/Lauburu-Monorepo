import { io, Socket } from 'socket.io-client';

export class SocketService {
    private socket: Socket;

    constructor(serverUrl: string) {
        this.socket = io(serverUrl);
    }

    public connect(): void {
        this.socket.connect();
    }

    public disconnect(): void {
        this.socket.disconnect();
    }

    public onMessage(callback: (message: any) => void): void {
        this.socket.on('message', callback);
    }

    public sendMessage(message: any): void {
        this.socket.emit('message', message);
    }
}