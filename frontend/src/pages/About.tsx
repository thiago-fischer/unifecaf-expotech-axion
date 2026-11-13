export default function About() {
  return (
    <div className="about">
      <p className="about-intro">
        O Axion é uma linha de produção inteligente em escala reduzida, desenvolvida para a ExpoTech
        2026.2, na categoria NEXUS.
      </p>
      <section aria-labelledby="como-funciona">
        <h2 id="como-funciona">Como funciona</h2>
        <ol className="about-flow">
          <li>
            <h3>Monte a ordem</h3>
            <p>
              Escolha os produtos e as quantidades. A receita de cada produto define as etapas,
              máquinas e tempos.
            </p>
          </li>
          <li>
            <h3>Calcule o plano</h3>
            <p>
              Veja no gráfico de Gantt quando cada máquina trabalha e quanto tempo a ordem leva.
            </p>
          </li>
          <li>
            <h3>Acompanhe a execução</h3>
            <p>Veja a movimentação das peças na maquete virtual conectada ao servidor.</p>
          </li>
        </ol>
      </section>
      <section aria-labelledby="como-planeja">
        <h2 id="como-planeja">Como o algoritmo planeja</h2>
        <div className="about-algorithm">
          <article className="panel">
            <h3>Algoritmo genético</h3>
            <p>
              Testa várias sequências, combina as mais promissoras e faz pequenas mudanças para
              tentar reduzir o tempo até a última peça ficar pronta.
            </p>
          </article>
          <article className="panel">
            <h3>Verificação com CP-SAT</h3>
            <p>
              Busca um plano mais rápido e, quando possível, comprova o menor tempo dentro do modelo
              de planejamento.
            </p>
          </article>
        </div>
        <p>Cada peça segue a ordem de suas etapas, e cada máquina atende uma peça por vez.</p>
      </section>
    </div>
  );
}
