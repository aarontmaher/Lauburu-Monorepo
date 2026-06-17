import React from 'react';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import { useEffect, useState } from 'react';
import { SocketService } from '../services/socketService';

const ChatWindow: React.FC = () => {
    const [messages, setMessages] = useState<string[]>([]);
    const socketService = new SocketService();

    useEffect(() => {
        socketService.connect();

        socketService.onMessage((message: string) => {
            setMessages(prevMessages => [...prevMessages, message]);
        });

        return () => {
            socketService.disconnect();
        };
    }, [socketService]);

    const handleSendMessage = (message: string) => {
        socketService.sendMessage(message);
    };

    return (
        <div className="chat-window">
            <MessageList messages={messages} />
            <MessageInput onSendMessage={handleSendMessage} />
        </div>
    );
};

export default ChatWindow;