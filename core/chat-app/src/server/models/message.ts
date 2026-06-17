export interface Message {
    sender: string;
    content: string;
    timestamp: Date;
}

export class MessageModel {
    private messages: Message[] = [];

    public async create(message: Message): Promise<void> {
        this.addMessage(message);
    }

    public addMessage(message: Message): void {
        this.messages.push(message);
    }

    public getMessages(): Message[] {
        return this.messages;
    }
}
