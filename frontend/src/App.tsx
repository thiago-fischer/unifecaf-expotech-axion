import { useState } from 'react';
import { Machines, Orders, Products } from './pages/Catalog';
import Planning from './pages/Planning';
import type { Area, Navigate } from './components/Common';

const areas: Area[] = ['Máquinas', 'Produtos', 'Ordens', 'Planejamento'];
const descriptions: Record<Area, string> = {
  Máquinas: 'Organize as estações da sua linha de produção.',
  Produtos: 'Transforme etapas e tempos em receitas de produção.',
  Ordens: 'Reúna os produtos que você precisa produzir.',
  Planejamento: 'Da demanda à programação das operações.',
};

export default function App() {
  const [area, setArea] = useState<Area>('Máquinas');
  const [orderId, setOrderId] = useState<number>();
  const navigate: Navigate = (next, order) => {
    setArea(next);
    setOrderId(order);
  };
  return (
    <div className="app-shell">
      <a className="skip-link" href="#conteudo">
        Pular para o conteúdo
      </a>
      <aside className="sidebar">
        <a className="brand" href="#conteudo" onClick={() => navigate('Máquinas')}>
          <span className="brand-mark">A</span>axion<span className="brand-dot">.</span>
        </a>
        <p className="sidebar-label">LINHA DE PRODUÇÃO</p>
        <nav aria-label="Navegação principal">
          {areas.map((item, index) => (
            <button
              key={item}
              aria-current={area === item ? 'page' : undefined}
              onClick={() => navigate(item)}
            >
              <span>0{index + 1}</span>
              {item}
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="local-dot" />
          Ambiente local<small>ExpoTech 2026.2 · NEXUS</small>
        </div>
      </aside>
      <main id="conteudo" tabIndex={-1}>
        <header>
          <div className="eyebrow">AXION / {area.toLocaleUpperCase('pt-BR')}</div>
          <h1>{area}</h1>
          <p>{descriptions[area]}</p>
        </header>
        {area === 'Máquinas' && <Machines />}
        {area === 'Produtos' && <Products navigate={navigate} />}
        {area === 'Ordens' && <Orders navigate={navigate} />}
        {area === 'Planejamento' && <Planning initialOrder={orderId} navigate={navigate} />}
        <footer>Axion · Planejamento local da produção</footer>
      </main>
    </div>
  );
}
