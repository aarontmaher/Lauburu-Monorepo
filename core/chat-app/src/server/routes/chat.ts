import { Router } from 'express';
import { ChatController } from '../controllers/chatController';

const router = Router();
const chatController = new ChatController();

router.post('/send', chatController.sendMessage);
router.get('/messages', chatController.getMessages);

export default router;