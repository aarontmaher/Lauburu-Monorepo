import { ChatWindow } from './components/ChatWindow';
import { MessageList } from './components/MessageList';
import { MessageInput } from './components/MessageInput';
import { SocketService } from './services/socketService';

class App {
    private chatWindow: ChatWindow;
    private messageList: MessageList;
    private messageInput: MessageInput;
    private socketService: SocketService;

    constructor() {
        this.socketService = new SocketService();
        this.chatWindow = new ChatWindow();
        this.messageList = new MessageList();
        this.messageInput = new MessageInput();

        this.initialize();
    }

    private initialize() {
        this.chatWindow.render();
        this.messageList.render();
        this.messageInput.render();

        this.socketService.onMessage((message) => {
            this.messageList.addMessage(message);
        });

        this.messageInput.onSend((content) => {
            const message = {
                sender: 'User', // Replace with actual user data
                content: content,
                timestamp: new Date().toISOString()
            };
            this.socketService.sendMessage(message);
            this.messageList.addMessage(message);
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new App();
});