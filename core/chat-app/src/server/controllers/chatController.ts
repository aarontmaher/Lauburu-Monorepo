import { ChatService } from '../services/chatService';

export class ChatController {
    private chatService: ChatService;

    constructor(chatService: ChatService = new ChatService()) {
        this.chatService = chatService;
        this.sendMessage = this.sendMessage.bind(this);
        this.getMessages = this.getMessages.bind(this);
    }

    public async sendMessage(req: any, res: any): Promise<void> {
        try {
            const { sender, content } = req.body;
            const message = await this.chatService.saveMessage(sender, content);
            res.status(201).json(message);
        } catch (error) {
            res.status(500).json({ error: 'Failed to send message' });
        }
    }

    public async getMessages(req: any, res: any): Promise<void> {
        try {
            const messages = await this.chatService.getMessages();
            res.status(200).json(messages);
        } catch (error) {
            res.status(500).json({ error: 'Failed to retrieve messages' });
        }
    }
}
