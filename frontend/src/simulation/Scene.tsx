import { useEffect, useRef, useState } from 'react';
import * as T from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { colors, positions, pose, type State } from './engine';

export default function Scene({
  state,
  select,
  reset,
  reduced,
}: {
  state: React.RefObject<State>;
  select: (id: string) => void;
  reset: number;
  reduced: boolean;
}) {
  const host = useRef<HTMLDivElement>(null);
  const choose = useRef(select);
  choose.current = select;
  const [error, setError] = useState('');
  useEffect(() => {
    const container = host.current!;
    setError('');
    let renderer: T.WebGLRenderer;
    try {
      renderer = new T.WebGLRenderer({ antialias: true });
    } catch {
      setError(
        'Visualização 3D indisponível. A simulação e a lista de unidades continuam disponíveis abaixo.',
      );
      return;
    }
    renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = T.PCFShadowMap;
    renderer.setClearColor('#0b141d');
    renderer.toneMapping = T.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.4;
    container.appendChild(renderer.domElement);
    renderer.domElement.setAttribute(
      'aria-label',
      'Maquete virtual 3D. Arraste para girar; use a lista abaixo para selecionar unidades.',
    );
    const scene = new T.Scene();
    scene.fog = new T.Fog('#0b141d', 45, 100);
    const camera = new T.PerspectiveCamera(38, 1, 0.1, 150);
    camera.position.set(14, 14, 28);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(3.6, 0, 0);
    controls.minDistance = 24;
    controls.maxDistance = 100;
    controls.maxPolarAngle = Math.PI * 0.46;
    controls.minPolarAngle = 0.25;
    controls.enablePan = false;
    controls.update();
    scene.add(new T.HemisphereLight('#b2d9ef', '#243042', 2));
    const light = new T.DirectionalLight('#fff1d5', 4);
    light.position.set(-8, 20, 12);
    light.castShadow = true;
    light.shadow.mapSize.set(2048, 2048);
    Object.assign(light.shadow.camera, { left: -28, right: 28, top: 18, bottom: -18, far: 70 });
    light.shadow.bias = -0.001;
    scene.add(light);
    const rim = new T.DirectionalLight('#50b9ff', 3);
    rim.position.set(8, 8, -12);
    scene.add(rim);
    const resources: T.Texture[] = [];
    function box(
      w: number,
      h: number,
      d: number,
      x: number,
      y: number,
      z: number,
      color: string,
      parent: T.Object3D = scene,
    ) {
      const m = new T.Mesh(
        new RoundedBoxGeometry(w, h, d, 2, Math.min(0.07, h / 4)),
        new T.MeshStandardMaterial({ color, roughness: 0.4, metalness: 0.45 }),
      );
      m.position.set(x, y, z);
      m.castShadow = true;
      m.receiveShadow = true;
      parent.add(m);
      return m;
    }
    function text(value: string, x: number, y: number, z: number, width = 2, color = '#b7c9da') {
      const canvas = document.createElement('canvas');
      canvas.width = 512;
      canvas.height = 128;
      const ctx = canvas.getContext('2d')!;
      const texture = new T.CanvasTexture(canvas);
      resources.push(texture);
      const sprite = new T.Sprite(new T.SpriteMaterial({ map: texture, depthTest: false }));
      sprite.position.set(x, y, z);
      sprite.scale.set(width, width / 4, 1);
      scene.add(sprite);
      const update = (v: string) => {
        ctx.clearRect(0, 0, 512, 128);
        ctx.fillStyle = color;
        ctx.font = '600 40px Segoe UI';
        ctx.textAlign = 'center';
        ctx.fillText(v, 256, 77);
        texture.needsUpdate = true;
      };
      update(value);
      return Object.assign(update, { sprite });
    }
    box(32, 0.5, 6.2, 4, -0.3, 0, '#263747');
    box(31.7, 0.05, 5.9, 4, 0, 0, '#3a4b57');
    for (const x of [-11, 19]) {
      box(0.4, 4.7, 0.45, x, 2.1, -0.8, '#687c8c');
      box(1.1, 0.14, 1.2, x, 0.12, -0.8, '#182834');
    }
    box(30.5, 0.45, 0.45, 4, 4.3, -0.8, '#78909c');
    box(30.5, 0.12, 0.12, 4, 4.3, -0.49, '#d5e4e9');
    // Visible threaded screw running along the single horizontal axis.
    const screw = new T.Group();
    screw.position.set(4, 4.3, -0.4);
    scene.add(screw);
    const shaft = new T.Mesh(
      new T.CylinderGeometry(0.055, 0.055, 30, 12),
      new T.MeshStandardMaterial({ color: '#dce5e9', metalness: 0.85, roughness: 0.25 }),
    );
    shaft.rotation.z = Math.PI / 2;
    screw.add(shaft);
    for (let i = 0; i < 150; i++) {
      const ring = new T.Mesh(new T.TorusGeometry(0.075, 0.018, 4, 8), shaft.material);
      ring.rotation.y = Math.PI / 2;
      ring.position.x = -15 + i * 0.2;
      screw.add(ring);
    }
    const carriage = new T.Group();
    scene.add(carriage);
    box(0.8, 0.6, 0.7, 0, 4.3, -0.6, '#edb454', carriage);
    const rod = box(0.12, 2, 0.12, 0, 3.2, 0, '#b9cbd8', carriage);
    const head = box(0.8, 0.18, 0.7, 0, 1.7, 0, '#f3bd5f', carriage);
    const claws = [
      box(0.1, 0.45, 0.12, -0.36, 1.45, 0, '#d5e4e9', carriage),
      box(0.1, 0.45, 0.12, 0.36, 1.45, 0, '#d5e4e9', carriage),
    ];
    const displays: Record<string, (s: string) => void> = {};
    const lamps: Record<string, T.Mesh> = {};
    Object.entries(positions).forEach(([name, x]) => {
      const machine = name.startsWith('M');
      box(
        machine ? 2.4 : 0.68,
        0.65,
        machine ? 2.2 : 0.85,
        x,
        0.35,
        0,
        machine ? '#263b4e' : '#1d303e',
      );
      box(machine ? 1.3 : 0.65, 0.09, 0.85, x, 0.73, 0, '#7b8c97');
      if (machine) {
        box(2.2, 1.8, 0.45, x, 1.3, -1.05, '#435e71');
        box(1.8, 0.6, 0.08, x, 1.6, -0.79, '#091b25');
        displays[name] = text('LIVRE', x, 1.65, -0.7, 1.7, '#66f1cb');
        text(name, x, 0.35, 1.3, 1.8);
        lamps[name] = box(0.16, 0.16, 0.18, x + 0.8, 2.35, -1, '#56edb9');
        for (let j = 0; j < 4; j++) box(0.5, 0.035, 0.06, x - 0.4, 1 + j * 0.12, -0.8, '#152c3c');
      } else if (!/^(IN|OUT|REJ)/.test(name)) text(name, x, 0.3, 1.15, 1.3);
    });
    text('ALMOXARIFADO', -8, 0, 2.1, 4);
    text('ESTOQUE AUXILIAR', 4.8, 0, 2.1, 3.5);
    text('VALIDAÇÃO', 7.3, 0, -2, 2.5);
    text('SAÍDA', 11.5, 0, 2.1, 3);
    text('REJEITADOS', 17, 0, 2.1, 3);
    text('AXION  /  NEXUS', 3, -0.1, 3.5, 5, '#e2edf3');
    const meshes: Record<string, T.Mesh> = {};
    const labels: Record<string, T.Sprite> = {};
    state.current.units.forEach((u) => {
      const mesh = box(0.52, 0.56, 0.52, positions[u.location], 1.05, 0, colors[u.product]);
      mesh.userData.id = u.id;
      meshes[u.id] = mesh;
      labels[u.id] = text(u.id.slice(-3), 0, 0, 0, 0.65, '#ffffff').sprite;
    });
    const ray = new T.Raycaster();
    let downX = 0,
      downY = 0;
    const down = (e: PointerEvent) => {
      downX = e.clientX;
      downY = e.clientY;
    };
    const click = (e: PointerEvent) => {
      if (Math.hypot(e.clientX - downX, e.clientY - downY) > 5) return;
      const r = renderer.domElement.getBoundingClientRect();
      ray.setFromCamera(
        new T.Vector2(
          ((e.clientX - r.left) / r.width) * 2 - 1,
          (-(e.clientY - r.top) / r.height) * 2 + 1,
        ),
        camera,
      );
      const hit = ray.intersectObjects(Object.values(meshes))[0];
      if (hit) choose.current(hit.object.userData.id);
    };
    renderer.domElement.addEventListener('pointerdown', down);
    renderer.domElement.addEventListener('pointerup', click);
    const resize = () => {
      const w = container.clientWidth,
        h = container.clientHeight;
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.position.copy(
        new T.Vector3(10.4, 14, 28)
          .normalize()
          .multiplyScalar(Math.max(34, 55 / camera.aspect))
          .add(controls.target),
      );
      controls.update();
      camera.updateProjectionMatrix();
    };
    const observer = new ResizeObserver(resize);
    observer.observe(container);
    resize();
    let dirty = true;
    controls.addEventListener('change', () => {
      dirty = true;
    });
    let lastTime = -1;
    let raf = 0,
      lastLabels = '';
    const render = () => {
      const s = state.current;
      if (!dirty && lastTime === s.time) {
        raf = requestAnimationFrame(render);
        return;
      }
      dirty = false;
      lastTime = s.time;
      const t = s.trip;
      const phaseTime = t
        ? Math.max(
            t.start,
            ...[t.approach, t.pickup, t.lifted, t.arrived, t.drop, t.end].filter(
              (time) => time <= s.time,
            ),
          )
        : s.time;
      const p = pose(reduced ? { ...s, time: phaseTime } : s);
      carriage.position.x = p.x;
      screw.rotation.x = p.x * 8;
      const y = p.y;
      head.position.y = y;
      claws.forEach((c) => (c.position.y = y - 0.22));
      rod.position.y = (4.1 + y) / 2;
      rod.scale.y = (4.1 - y) / 2;
      for (const u of s.units) {
        const m = meshes[u.id];
        if (u.location === 'TRANS') {
          const t = s.trip!;
          m.position.set(p.carrying ? p.x : positions[t.to], p.carrying ? y - 0.38 : 1.05, 0);
        } else m.position.set(positions[u.location], 1.05, 0);
        labels[u.id].position.copy(m.position).add(new T.Vector3(0, 0.5, 0));
      }
      const labelKey = Math.floor(s.time * 5).toString() + s.status;
      if (labelKey !== lastLabels) {
        lastLabels = labelKey;
        for (const name of ['M1', 'M2', 'M3']) {
          const u = s.units.find((u) => u.location === name);
          displays[name](
            u
              ? u.until
                ? `${u.product} · E${u.step + 1} · ${Math.max(0, u.until - s.time).toFixed(1)}s`
                : `${u.product} · AGUARDA`
              : 'LIVRE',
          );
          (lamps[name].material as T.MeshStandardMaterial).color.set(
            u?.until ? '#52f5bb' : u ? '#ffc15b' : '#607d8b',
          );
        }
      }
      controls.update();
      renderer.render(scene, camera);
      raf = requestAnimationFrame(render);
    };
    render();
    const lost = (e: Event) => {
      e.preventDefault();
      setError(
        'Contexto gráfico perdido. Use a lista textual ou restaure a câmera para tentar novamente.',
      );
    };
    renderer.domElement.addEventListener('webglcontextlost', lost);
    return () => {
      cancelAnimationFrame(raf);
      observer.disconnect();
      controls.dispose();
      renderer.domElement.removeEventListener('pointerdown', down);
      renderer.domElement.removeEventListener('pointerup', click);
      renderer.domElement.removeEventListener('webglcontextlost', lost);
      scene.traverse((o) => {
        if (o instanceof T.Mesh) {
          o.geometry.dispose();
          const mats = Array.isArray(o.material) ? o.material : [o.material];
          mats.forEach((m) => m.dispose());
        }
        if (o instanceof T.Sprite) o.material.dispose();
      });
      resources.forEach((t) => t.dispose());
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, [state, reset, reduced]);
  return (
    <div className="sim-scene" ref={host}>
      {error && (
        <p className="sim-graphic-error" role="status">
          {error}
        </p>
      )}
    </div>
  );
}
