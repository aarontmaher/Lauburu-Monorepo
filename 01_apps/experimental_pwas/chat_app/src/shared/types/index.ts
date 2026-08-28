export interface Message {
    sender: string;
    content: string;
    timestamp: Date;
}

export interface User {
    id: string;
    username: string;
}