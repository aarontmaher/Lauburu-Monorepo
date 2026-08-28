import React from 'react';
import { Message } from '../../../shared/types';

interface MessageListProps {
    messages: Message[];
}

const MessageList: React.FC<MessageListProps> = ({ messages }) => {
    return (
        <ul className="message-list">
            {messages.map((message, index) => (
                <li key={index} className="message-item">
                    <strong>{message.sender}:</strong> {message.content}
                </li>
            ))}
        </ul>
    );
};

export default MessageList;