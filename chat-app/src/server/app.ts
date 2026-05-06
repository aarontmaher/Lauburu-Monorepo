import express from 'express';
import bodyParser from 'body-parser';
import path from 'path';
import chatRoutes from './routes/chat';
import athleteMemoryRoutes from './routes/athleteMemory';
import internalRoutes from './routes/internal';
import feedbackRoutes from './routes/feedback';
import backlogRoutes from './routes/backlog';
import integrationRoutes from './routes/integrations';
import mcpRoutes from './routes/mcpRoutes';
import { startAthleteRefreshScheduler } from './automation/athleteRefreshScheduler';
import { FilePrivateAthleteMemoryRepository } from './athlete-memory/file-private-athlete-memory-repository';
import { FileApiAiStateStore } from './athlete-memory/file-api-ai-state-store';

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
// Body limit is generous to accept tester feedback submissions that
// embed up to 3 base64-encoded screenshots (~800KB each after client
// compression) and WHOOP CSV exports (up to 20MB combined — a
// 5-year recoveries.csv + sleeps.csv bundle). Other routes accept
// small JSON payloads and are unaffected.
app.use(bodyParser.json({ limit: '25mb' }));
app.use(bodyParser.urlencoded({ extended: true, limit: '25mb' }));

// Routes
app.use('/api/chat', chatRoutes);
app.use('/api/athlete-memory', athleteMemoryRoutes);
app.use('/api/feedback', feedbackRoutes);
app.use('/api/backlog', backlogRoutes);
app.use('/api/integrations', integrationRoutes);
app.use('/api', mcpRoutes);
app.use('/v1/internal', internalRoutes);

const dataDir = path.resolve(__dirname, '../../data/private-athlete-memory');
const repository = new FilePrivateAthleteMemoryRepository(dataDir);
const apiAiStore = new FileApiAiStateStore(dataDir);

function startServer(port: string | number = PORT) {
  startAthleteRefreshScheduler(repository, { store: apiAiStore });
  return app.listen(port, () => {
    console.log(`Server is running on http://localhost:${port}`);
  });
}

if (require.main === module) {
  startServer();
}

export { app, startServer };
