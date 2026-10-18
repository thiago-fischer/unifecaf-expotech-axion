import { expect, test } from '@playwright/test';

test('cadastro completo e planejamento pela API real em desktop e celular', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Máquinas', exact: true })).toBeVisible();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Pular para o conteúdo' })).toBeFocused();
  const machineName = 'Estação de teste';
  for (let index = 0; index < 2; index++) {
    await page.getByLabel('Nome da máquina').fill(machineName);
    await page.getByRole('button', { name: 'Cadastrar máquina' }).click();
    await expect(page.getByRole('status').filter({ hasText: 'Máquina cadastrada' })).toContainText(
      'Máquina cadastrada',
    );
  }
  const machines = (await (await page.request.get('/api/machines')).json()) as {
    id: number;
    name: string;
  }[];
  const newMachines = machines.filter((machine) => machine.name === machineName);
  expect(newMachines).toHaveLength(2);
  const machineId = newMachines[0].id;
  expect(machineId).toBeGreaterThan(3);
  await page.getByRole('button', { name: `Consultar #${machineId}`, exact: true }).click();
  await expect(page.getByRole('region', { name: 'Consulta individual' })).toContainText(
    machineName,
  );
  await page.getByRole('button', { name: 'Voltar à lista' }).click();

  await page.getByRole('navigation').getByRole('button', { name: 'Produtos' }).click();
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
  await page.getByRole('button', { name: `Consultar #${productId}`, exact: true }).click();
  await expect(page.getByRole('region', { name: 'Consulta individual' })).toContainText('7 s');

  await page.getByRole('navigation').getByRole('button', { name: 'Ordens' }).click();
  await page.getByLabel('Produto do item 1').selectOption(String(productId));
  await page.getByLabel('Quantidade do item 1').fill('2');
  await page.getByRole('button', { name: 'Criar ordem' }).click();
  await expect(
    page.getByRole('status').filter({ hasText: 'produção não foi iniciada' }),
  ).toContainText('produção não foi iniciada');
  const orders = (await (await page.request.get('/api/orders')).json()) as { id: number }[];
  const orderId = orders.at(-1)!.id;
  await page.getByRole('button', { name: `Consultar #${orderId}`, exact: true }).click();
  await expect(page.getByRole('region', { name: 'Consulta individual' })).toContainText('2 un.');
  await page.getByRole('button', { name: `Planejar ordem #${orderId}` }).click();
  await expect(page.getByLabel('Ordem de produção')).toHaveValue(String(orderId));
  const response = page.waitForResponse((response) =>
    response.url().endsWith(`/orders/${orderId}/plan`),
  );
  await page.getByRole('button', { name: 'Calcular planejamento' }).click();
  const httpResponse = await response;
  expect(httpResponse.status()).toBe(200);
  const plan = await httpResponse.json();
  const result = page.getByRole('region', { name: 'Resultado do planejamento' });
  await expect(result).toBeVisible();
  await expect(result).toContainText(`${plan.metrics.makespan_seconds} s`);
  expect(plan.metrics.makespan_seconds).toBe(22);
  await expect(result.getByRole('row')).toHaveCount(5);
  await expect(result).toContainText('Ótimo comprovado');
  await expect(result).toContainText('não habilita execução física');
  await page.screenshot({ path: 'test-results/desktop-planning.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole('heading', { name: 'Planejamento', exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.getByRole('region', { name: 'Tabela de operações' }).focus();
  await expect(page.getByRole('region', { name: 'Tabela de operações' })).toBeFocused();
  await page.screenshot({ path: 'test-results/mobile-planning.png', fullPage: true });
});
