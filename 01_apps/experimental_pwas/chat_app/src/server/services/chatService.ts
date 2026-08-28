import { Message, MessageModel } from '../models/message';

export class ChatService {
    private messages: Message[] = [];
    private messageModel = new MessageModel();

    public async saveMessage(sender: string, content: string): Promise<Message> {
        const message: Message = {
            sender,
            content,
            timestamp: new Date(),
        };
        this.messages.push(message);
        await this.messageModel.create(message);
        return message;
    }

    public async getMessages(): Promise<Message[]> {
        return this.messages;
    }
}
