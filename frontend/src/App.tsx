import { lazy, Suspense, useState } from 'react';
import { Production } from './pages/Catalog';
import Planning from './pages/Planning';
import About from './pages/About';
import type { Area, Navigate } from './components/Common';
import logo from './assets/axion.png';

const Simulation = lazy(() => import('./pages/Simulation'));
const areas: Area[] = ['Produção', 'Planejamento', 'Maquete virtual', 'Sobre'];

export default function App() {
  const [area, setArea] = useState<Area>('Produção');
  const [orderId, setOrderId] = useState<number>();
  const navigate: Navigate = (next, order) => {
    setArea(next);
    setOrderId(order);
  };

  return (
    <>
      <a className="skip-link" href="#conteudo">
        Pular para o conteúdo
      </a>
      <header className="app-header">
        <div className="header-inner">
          <a className="brand" href="#conteudo" onClick={() => navigate('Produção')}>
            <img src={logo} alt="AXION" />
          </a>
          <nav aria-label="Navegação principal">
            {areas.map((item) => (
              <button
                key={item}
                aria-current={area === item ? 'page' : undefined}
                onClick={() => {
                  if (item !== area) navigate(item);
                }}
              >
                {item}
              </button>
            ))}
          </nav>
        </div>
      </header>
      <main id="conteudo" tabIndex={-1}>
        <h1>{area === 'Sobre' ? 'Sobre o Axion' : area}</h1>
        {area === 'Produção' && <Production navigate={navigate} />}
        {area === 'Planejamento' && <Planning initialOrder={orderId} navigate={navigate} />}
        {area === 'Maquete virtual' && (
          <Suspense fallback={<p role="status">Carregando maquete…</p>}>
            <Simulation initialOrder={orderId} />
          </Suspense>
        )}
        {area === 'Sobre' && <About />}
      </main>
    </>
  );
}
