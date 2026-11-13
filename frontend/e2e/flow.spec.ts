import { expect, test } from '@playwright/test';

test('cadastro completo e planejamento pela API real em desktop e celular', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Produção', exact: true })).toBeVisible();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Pular para o conteúdo' })).toBeFocused();
  await expect(page.getByRole('region', { name: 'Máquinas cadastradas' })).toContainText(
    'Torno CNC',
  );
  await expect(page.getByRole('button', { name: /Cadastrar máquina/ })).toHaveCount(0);
  const machines = (await (await page.request.get('/api/machines')).json()) as {
    id: number;
    name: string;
  }[];
  const machineId = machines.find((machine) => machine.name === 'Torno CNC')!.id;

  await page.getByRole('button', { name: 'Novo produto' }).click();
  await page.getByLabel('Nome do produto').fill('Peça de teste');
  await page.getByLabel('Máquina da etapa 1').selectOption(String(machineId));
  await page.getByLabel('Duração da etapa 1 (s)').fill('4');
  await page.getByRole('button', { name: 'Adicionar etapa' }).click();
  await page.getByLabel('Máquina da etapa 2').selectOption(String(machineId));
  await page.getByLabel('Duração da etapa 2 (s)').fill('7');
  await page.getByRole('button', { name: 'Cadastrar produto' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Produto cadastrado' })).toContainText(
    'Produto cadastrado',
  );
  const products = (await (await page.request.get('/api/products')).json()) as {
    id: number;
    name: string;
  }[];
  const productId = products.find((product) => product.name === 'Peça de teste')!.id;
  const product = page.locator('summary').filter({ hasText: 'Peça de teste' });
  await product.click();
  await expect(product.locator('..')).toContainText('7 s');
  await page.screenshot({ path: 'test-results/desktop-production.png', fullPage: true });

  await page.getByLabel('Produto do item 1').selectOption(String(productId));
  await page.getByLabel('Quantidade do item 1').fill('2');
  await page.getByRole('button', { name: 'Criar ordem' }).click();
  await expect(page.getByRole('status').filter({ hasText: /Ordem #\d+ criada/ })).toBeVisible();
  const orders = (await (await page.request.get('/api/orders')).json()) as { id: number }[];
  const orderId = orders.at(-1)!.id;
  await page.getByText('Ordens registradas', { exact: true }).click();
  await page.getByText(`Ordem #${orderId}`, { exact: true }).click();
  await expect(page.getByText('Peça de teste · 2 un.')).toBeVisible();
  await page.getByRole('button', { name: `Planejar ordem #${orderId}` }).click();
  await expect(page.getByLabel('Ordem de produção')).toHaveValue(String(orderId));
  const response = page.waitForResponse((response) =>
    response.url().endsWith(`/orders/${orderId}/plan`),
  );
  await page.getByRole('button', { name: 'Calcular OP' }).click();
  const httpResponse = await response;
  expect(httpResponse.status()).toBe(200);
  const plan = await httpResponse.json();
  const result = page.getByRole('region', { name: 'Resultado do planejamento' });
  await expect(result).toBeVisible();
  await expect(result).toContainText(`${plan.metrics.makespan_seconds} s`);
  expect(plan.metrics.makespan_seconds).toBe(22);
  await expect(result.getByRole('region', { name: 'Gráfico de Gantt por máquina' })).toBeVisible();
  await expect(result.getByRole('table')).not.toBeVisible();
  await expect(result).toContainText('Ótimo comprovado');
  await page.screenshot({ path: 'test-results/desktop-planning.png', fullPage: true });
  const tableToggle = result.getByText(/^Tabela de operações/);
  await tableToggle.focus();
  await page.keyboard.press('Enter');
  await expect(result.getByRole('row')).toHaveCount(5);
  await page.keyboard.press('Enter');
  await expect(result.getByRole('table')).not.toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole('heading', { name: 'Planejamento', exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.getByRole('region', { name: 'Cronograma por máquina em segundos' }).focus();
  await expect(
    page.getByRole('region', { name: 'Cronograma por máquina em segundos' }),
  ).toBeFocused();
  await page.screenshot({ path: 'test-results/mobile-planning.png', fullPage: true });
});

test('Gantt com produtos simultâneos e três máquinas da API real', async ({ page }) => {
  const products = (await (await page.request.get('/api/products')).json()) as {
    id: number;
    name: string;
  }[];
  const quantities = new Map([
    ['Eixo escalonado', 3],
    ['Placa de fixação', 1],
    ['Suporte usinado', 2],
  ]);
  const items = products
    .filter((product) => quantities.has(product.name))
    .map((product) => ({ product_id: product.id, quantity: quantities.get(product.name) }));
  expect(items).toHaveLength(3);
  const orderResponse = await page.request.post('/api/orders', { data: { items } });
  expect(orderResponse.status()).toBe(201);
  const order = await orderResponse.json();
  await page.goto('/');
  await page.getByRole('navigation').getByRole('button', { name: 'Planejamento' }).click();
  await page.getByLabel('Ordem de produção').selectOption(String(order.id));
  await page.getByRole('button', { name: 'Calcular OP' }).click();
  const chart = page.getByRole('region', { name: 'Gráfico de Gantt por máquina' });
  await expect(chart).toBeVisible();
  await expect(chart.getByRole('img')).toHaveCount(14);
  await expect(chart).toContainText('Torno CNC');
  await expect(chart).toContainText('Fresadora CNC');
  await expect(chart).toContainText('Centro de Usinagem CNC');
  await page.screenshot({ path: 'test-results/desktop-gantt.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.screenshot({ path: 'test-results/mobile-gantt.png', fullPage: true });
});

test('guia Sobre apresenta o projeto e a busca pelo menor tempo', async ({ page }) => {
  await page.goto('/');
  const nav = page.getByRole('navigation');
  await expect(nav.getByRole('button')).toHaveText([
    'Produção',
    'Planejamento',
    'Maquete virtual',
    'Sobre',
  ]);
  await expect(page.getByRole('img', { name: 'AXION' })).toBeVisible();
  await nav.getByRole('button', { name: 'Sobre' }).click();
  await expect(page.getByRole('heading', { name: 'Sobre o Axion' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Como funciona' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Algoritmo genético' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Verificação com CP-SAT' })).toBeVisible();
  await page.screenshot({ path: 'test-results/desktop-about.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(nav.getByRole('button', { name: 'Sobre' })).toBeInViewport();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await nav.getByRole('button', { name: 'Produção' }).click();
  await expect(page.getByRole('heading', { name: 'Nova ordem de produção' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
});
