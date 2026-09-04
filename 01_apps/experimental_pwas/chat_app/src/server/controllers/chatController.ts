import { ChatService } from '../services/chatService';
import { EdgeAIChatRouter, DeviceProfile } from '../services/edgeAIChatRouter';

export class ChatController {
    private chatService: ChatService;

    constructor(chatService: ChatService = new ChatService()) {
        this.chatService = chatService;
        this.sendMessage = this.sendMessage.bind(this);
        this.getMessages = this.getMessages.bind(this);
    }

    public async sendMessage(req: any, res: any): Promise<void> {
        try {
            const { sender, content, device } = req.body;
            
            // 1. Save user message
            const userMsg = await this.chatService.saveMessage(sender || 'User', content);

            // 2. Parse client device profile (or infer from headers)
            const deviceProfile: DeviceProfile = device || {
                platform: (req.headers['sec-ch-ua-platform'] || '').toLowerCase().includes('android') ? 'android' : 'web',
                ramGb: req.body.ramGb || 4.0
            };

            // 3. Generate Edge AI Response using device-specific model
            const history = (await this.chatService.getMessages()).map(m => ({
                role: m.sender === 'AI_Assistant' ? 'assistant' : 'user',
                content: m.content
            }));

            const aiResponse = await EdgeAIChatRouter.generateResponse(history, deviceProfile);

            // 4. Save and return AI response
            const aiMsg = await this.chatService.saveMessage(
                `AI_Assistant (${aiResponse.model.name})`,
                aiResponse.text
            );

            res.status(201).json({
                userMessage: userMsg,
                aiMessage: aiMsg,
                modelUsed: aiResponse.model,
                latencyMs: aiResponse.latencyMs
            });
        } catch (error) {
            console.error('ChatController error:', error);
            res.status(500).json({ error: 'Failed to process edge chat message' });
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

