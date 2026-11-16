import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import Network from './Network';
import { json } from '../test/fixtures';

const overview = {
  capture_session_id: '3ad3548c-8ac3-4b05-9eb4-f309c2604561',
  last_event_at: null,
  last_batch_age_ms: null,
  services: {
    backend: { state: 'online', detail: null },
    capture: { state: 'disabled', detail: null },
    grafana: { state: 'offline', detail: 'indisponível' },
  },
  connections: [{ source: 'frontend', destination: 'backend', visibility: 'configured' }],
  security: {
    controller_token_configured: true,
    capture_token_configured: false,
    local_http_without_tls: true,
    ports_restricted_to_host: true,
    raw_capture_storage_disabled: true,
    accepted_batches: 4,
    blocked_batches: 1,
  },
  grafana_public_url: 'http://127.0.0.1:3000',
  grafana_dashboard_uid: 'axion-rede-comunicacao',
};

it('mostra serviços, alcance da topologia e captura desativada', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string) =>
      json(
        path.includes('/network/events')
          ? {
              capture_session_id: overview.capture_session_id,
              events: [],
              next_sequence: 0,
              history_lost: false,
              session_changed: false,
              last_batch_age_ms: null,
            }
          : overview,
      ),
    ),
  );
  render(<Network />);
  expect(await screen.findByRole('heading', { name: 'Componentes' })).toBeVisible();
  expect(screen.getByText('configured')).toBeVisible();
  expect(screen.queryByRole('link', { name: /Grafana/ })).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('tab', { name: 'Captura ao vivo' }));
  expect(screen.getByText('Captura desativada')).toBeVisible();
});

it('expõe apenas indicadores de segurança e o aviso de HTTP local', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => json(overview)),
  );
  render(<Network />);
  await screen.findByRole('heading', { name: 'Componentes' });
  await userEvent.click(screen.getByRole('tab', { name: 'Segurança' }));
  expect(screen.getByText(/Token do controlador: configurado/)).toBeVisible();
  expect(screen.getByText(/HTTP local/)).toBeVisible();
  expect(screen.getByText(/Lotes aceitos nesta execução: 4/)).toBeVisible();
  expect(screen.getByRole('link', { name: /documentação/ })).toHaveAttribute(
    'href',
    '/network-lab.md',
  );
});
