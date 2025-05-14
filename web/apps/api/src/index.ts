console.log('API server starting...');

// Basic express server setup (example)
import express from 'express';

const app = express();
const port = process.env.PORT || 3001; // Ensure API runs on a different port than the web app

app.get('/', (req, res) => {
  res.send('Clarity API is running!');
});

app.listen(port, () => {
  console.log(`API server listening on http://localhost:${port}`);
}); 