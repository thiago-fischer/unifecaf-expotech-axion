import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import ScenePreview from './pages/ScenePreview';
import './styles.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>{window.location.pathname === '/preview' ? <ScenePreview /> : <App />}</StrictMode>,
);
