import { lazy, Suspense } from 'react';
import './scene-preview.css';

const Simulation = lazy(() => import('./Simulation'));

export default function ScenePreview() {
  return (
    <main className="scene-preview">
      <header className="scene-preview-header">
        <div>
          <span>AXION · MODO DE DESENVOLVIMENTO</span>
          <h1>Pré-visualização da maquete</h1>
          <p>Edite a cena e salve o arquivo para ver as alterações aqui.</p>
        </div>
        <a href="/">Abrir aplicação</a>
      </header>
      <Suspense fallback={<p>Carregando maquete…</p>}>
        <Simulation />
      </Suspense>
    </main>
  );
}
