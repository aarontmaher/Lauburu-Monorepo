import React, { useState } from 'react';

const MessageInput = ({ onSend }) => {
    const [message, setMessage] = useState('');

    const handleChange = (event) => {
        setMessage(event.target.value);
    };

    const handleSubmit = (event) => {
        event.preventDefault();
        if (message.trim()) {
            onSend(message);
            setMessage('');
        }
    };

    return (
        <form onSubmit={handleSubmit}>
            <input
                type="text"
                value={message}
                onChange={handleChange}
                placeholder="Type your message..."
                required
            />
            <button type="submit">Send</button>
        </form>
    );
};

export default MessageInput;