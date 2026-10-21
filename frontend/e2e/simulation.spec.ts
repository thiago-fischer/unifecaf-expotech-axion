import { test, expect } from '@playwright/test';
test('maquete independente da API, controles e ciclo completo', async ({ page }) => {
  await page.route('http://127.0.0.1:5174/api/**', (r) => r.abort());
  await page.goto('/');
  await page.getByRole('button', { name: /Simulação/ }).click();
  await expect(page.locator('.sim-scene canvas')).toBeVisible();
  await page.getByRole('button', { name: 'Iniciar', exact: true }).click();
  await expect(page.getByRole('status')).toHaveText('Em execução');
  await page.getByRole('button', { name: 'Pausar', exact: true }).click();
  const time = await page.locator('.sim-metrics').innerText();
  await page.waitForTimeout(200);
  expect(await page.locator('.sim-metrics').innerText()).toBe(time);
  await page.getByRole('button', { name: 'Reiniciar', exact: true }).click();
  for (
    let i = 0;
    i < 350 && !(await page.getByRole('status').innerText()).includes('concluído');
    i++
  )
    await page.getByRole('button', { name: 'Próximo evento', exact: true }).dispatchEvent('click');
  await expect(page.getByRole('status')).toHaveText('Ciclo concluído');
  await expect(page.locator('.sim-metrics')).toContainText('6 / 6');
  await page.getByRole('button', { name: 'MAT-001', exact: false }).click();
  await expect(page.locator('.sim-history')).toContainText('Validação aprovada');
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.getByRole('button', { name: 'Reiniciar', exact: true }).click();
  await expect(page.getByRole('status')).toHaveText('Pronta para iniciar');
});

test('sem WebGL mantém controles, teclado e rastreabilidade', async ({ page }) => {
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
  await page.getByRole('button', { name: /Simulação/ }).click();
  await expect(page.getByText(/Visualização 3D indisponível/)).toBeVisible();
  const next = page.getByRole('button', { name: 'Próximo evento', exact: true });
  await next.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('status').filter({ hasText: 'Pausada' })).toBeVisible();
  await page.getByLabel('Movimento reduzido').check();
  await page.getByRole('button', { name: 'MAT-002', exact: false }).click();
  await expect(page.locator('.sim-history')).toContainText('MAT-002');
});
