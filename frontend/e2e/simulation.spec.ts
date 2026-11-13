import { expect, test } from '@playwright/test';

test('executa uma ordem na maquete conectada e restaura o controlador', async ({ page }) => {
  const machines = await (await page.request.get('/api/machines')).json();
  const machine = machines.find((item: { name: string }) => item.name === 'Torno CNC');
  const productResponse = await page.request.post('/api/products', {
    data: {
      name: 'Peça para simulação',
      steps: [{ sequence: 1, machine_id: machine.id, processing_time_seconds: 1 }],
    },
  });
  expect(productResponse.status()).toBe(201);
  const product = await productResponse.json();
  const orderResponse = await page.request.post('/api/orders', {
    data: { items: [{ product_id: product.id, quantity: 1 }] },
  });
  expect(orderResponse.status()).toBe(201);
  const order = await orderResponse.json();

  await page.goto('/');
  await page.getByRole('button', { name: 'Maquete virtual' }).click();
  const simulation = page.getByRole('region', { name: 'Execução da maquete pelo servidor' });
  const status = simulation.locator('.sim-status');
  await expect(status).toHaveText('Aguardando uma OP');
  await expect(page.locator('.sim-scene canvas')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Demonstração local' })).toHaveCount(0);
  await page.getByLabel('Velocidade').selectOption('4');
  await page.getByLabel('Ordem de produção').selectOption(String(order.id));
  await page.getByText('Associação de estações').click();
  await expect(page.getByLabel(/Estação para Torno CNC/)).toHaveValue('M1');
  await page.getByText('Associação de estações').click();
  await page.getByRole('button', { name: 'Iniciar simulação' }).click();
  await expect(status).toHaveText('Ciclo concluído', { timeout: 35_000 });
  await page.getByText('Estações e peças').click();
  await expect(page.getByRole('button', { name: /SIM-001.*Aprovada/ })).toBeVisible();
  await page.screenshot({ path: 'test-results/desktop-simulation.png', fullPage: true });
  await page.getByRole('button', { name: 'Restaurar maquete' }).click();
  await expect(status).toHaveText('Aguardando uma OP');
  await expect(page.getByLabel('Velocidade')).toHaveValue('1');
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
});

test('sem WebGL mantém os controles e o acompanhamento do servidor', async ({ page }) => {
  await page.addInitScript(() => {
    const get = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (
      this: HTMLCanvasElement,
      type: string,
      ...args: unknown[]
    ) {
      if (type.includes('webgl')) return null;
      return Reflect.apply(get, this, [type, ...args]);
    } as typeof get;
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Maquete virtual' }).click();
  await expect(page.getByText(/Visualização 3D indisponível/)).toBeVisible();
  await expect(page.locator('.sim-status')).toHaveText('Aguardando uma OP');
  await page.getByLabel('Movimento reduzido').check();
  await page.getByText('Estações e peças').click();
  await expect(page.getByRole('button', { name: /SIM-001.*Almoxarifado/ })).toBeVisible();
});
