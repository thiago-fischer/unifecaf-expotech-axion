# ADR-008 — Maquete virtual com Three.js e motor local determinístico

- Status: Adotada na implementação autorizada da SPEC-0007; revisão por outro integrante pendente
- Data: 20/10/2026
- Relacionada: [SPEC-0007](../specs/0007-maquete-virtual.md)

## Contexto

O responsável autorizou implementar uma maquete animada com acabamento 3D,
independente do planejador inicial e sem integração com hardware. O frontend
React/TypeScript/Vite está definido pela ADR-007.

## Decisão

Usar Three.js diretamente em um componente React, carregado sob demanda ao
abrir Simulação. Usar OrbitControls e geometrias arredondadas do próprio pacote.
Versões exatas ficam em package.json e package-lock.json. Modelos, materiais e
texturas de texto são gerados localmente, sem assets remotos ou credenciais.

Separar motor de eventos em TypeScript puro, apresentação WebGL e controles
React. O motor mantém precedências, capacidade, reservas e relógio simulado;
a cena interpola posições a partir desse estado. React atualiza indicadores
em frequência limitada, sem reconstruir a cena a cada quadro. Desmontagem
libera controles, observadores, animações, geometrias, materiais e texturas.

Esta lógica é exclusiva da demonstração local. Backend e otimizador continuam
em Python e não mudam de responsabilidade. Não há novos endpoints ou migrations.

## Alternativas e justificativa

SVG/CSS atenderiam uma vista esquemática, mas exigiriam simular manualmente
perspectiva, iluminação e sombras. Three.js fornece esses recursos e seleção
por raycasting. Uma camada React adicional para a cena não é necessária para
este cenário pequeno com geometria estável; evitamos uma segunda abstração.
Uma engine física não é necessária: trajetórias são determinadas pelos eventos.

## Consequências

A simulação exige WebGL para a cena, com acompanhamento textual na ausência
de suporte. O chunk gráfico é maior que o limite de aviso padrão do Vite e
fica separado da navegação inicial via importação dinâmica. A qualidade e o
FPS dependem do dispositivo; a medição deve registrar ambiente e limitações.
Captura vertical é ilustrativa, sem decidir o mecanismo físico. O resultado
não é uma solução ótima nem uma validação em hardware.

## Referências

- [Documentação oficial do Three.js](https://threejs.org/docs/), consultada durante a implementação.
- [ADR-007](0007-react-frontend.md).
