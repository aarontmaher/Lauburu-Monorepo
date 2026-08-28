# Chat Application

This project is a real-time chat application built using TypeScript, Express, and WebSocket for real-time communication. It consists of a server-side application that handles chat logic and a client-side application that provides the user interface.

## Project Structure

```
chat-app
├── src
│   ├── server
│   │   ├── app.ts                # Entry point for the server application
│   │   ├── routes
│   │   │   └── chat.ts           # Chat routes for sending and receiving messages
│   │   ├── controllers
│   │   │   └── chatController.ts  # Controller for chat-related logic
│   │   ├── models
│   │   │   └── message.ts         # Message model defining the structure of a chat message
│   │   └── services
│   │       └── chatService.ts     # Service for managing chat messages and interactions
│   ├── client
│   │   ├── index.html             # Main HTML file for the client application
│   │   ├── styles
│   │   │   └── main.css           # CSS styles for the client application
│   │   └── scripts
│   │       ├── app.ts             # Entry point for the client-side application
│   │       ├── components
│   │       │   ├── ChatWindow.ts   # Main chat interface component
│   │       │   ├── MessageList.ts   # Component displaying a list of chat messages
│   │       │   └── MessageInput.ts   # Component for inputting and sending messages
│   │       └── services
│   │           └── socketService.ts # Service for managing WebSocket connections
│   └── shared
│       └── types
│           └── index.ts            # Shared types and interfaces
├── package.json                    # npm configuration file
├── tsconfig.json                   # TypeScript configuration file
└── README.md                       # Project documentation
```

## Setup Instructions

1. **Clone the repository:**
   ```
   git clone <repository-url>
   cd chat-app
   ```

2. **Install dependencies:**
   ```
   npm install
   ```

3. **Run the server:**
   ```
   npm run start
   ```

4. **Open the client:**
   Open `src/client/index.html` in your web browser to access the chat application.

## Usage Guidelines

- Users can send and receive messages in real-time.
- The chat interface allows users to view the message history and input new messages.
- Ensure that the server is running before accessing the client application.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.