import { useEffect, useRef, useState } from 'react';
import * as T from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import {
  bufferWidth,
  colors,
  conveyorCapacity,
  conveyorPitch,
  conveyorProgress,
  positionX,
  positions,
  pose,
  RFID_POSITION,
  stationWidth,
  type State,
} from './engine';

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
    const leftPost = positions.IN - 0.9;
    const rightPost = positions.OUT + 0.9;
    const centerX = (leftPost + rightPost) / 2;
    const span = rightPost - leftPost;
    const conveyorLength = conveyorCapacity * conveyorPitch + 0.35;
    const conveyorEnd = conveyorLength - 0.5;
    const camera = new T.PerspectiveCamera(38, 1, 0.1, 150);
    camera.position.set(14, 14, 28);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(centerX, 0.6, (conveyorEnd - 2.2) / 2);
    controls.minDistance = 9;
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
    function floor(width: number, depth: number, x: number, z: number) {
      box(width, 0.5, depth, x, -0.3, z, '#263747');
      box(width, 0.05, depth, x, 0, z, '#3a4b57');
    }
    const frontEdge = 2.35;
    const extensionDepth = conveyorEnd + 0.2 - frontEdge;
    floor(span + 1.4, frontEdge + 2.2, centerX, (frontEdge - 2.2) / 2);
    for (const x of [positions.IN, positions.OUT]) {
      floor(1.85, extensionDepth, x, frontEdge + extensionDepth / 2);
    }
    for (const x of [leftPost, rightPost]) {
      box(0.4, 4.7, 0.45, x, 2.1, -0.8, '#687c8c');
      box(1.1, 0.14, 1.2, x, 0.12, -0.8, '#182834');
    }
    box(span + 0.4, 0.45, 0.45, centerX, 4.3, -0.8, '#78909c');
    box(span + 0.4, 0.12, 0.12, centerX, 4.3, -0.49, '#d5e4e9');
    // Visible threaded screw running along the single horizontal axis.
    const screw = new T.Group();
    screw.position.set(centerX, 4.3, -0.4);
    scene.add(screw);
    const shaft = new T.Mesh(
      new T.CylinderGeometry(0.055, 0.055, span, 12),
      new T.MeshStandardMaterial({ color: '#dce5e9', metalness: 0.85, roughness: 0.25 }),
    );
    shaft.rotation.z = Math.PI / 2;
    screw.add(shaft);
    for (let x = -span / 2; x < span / 2; x += 0.2) {
      const ring = new T.Mesh(new T.TorusGeometry(0.075, 0.018, 4, 8), shaft.material);
      ring.rotation.y = Math.PI / 2;
      ring.position.x = x;
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
    const rfidX = RFID_POSITION;
    const armZ = -1.25;
    const rfidSensorZ = -0.18;
    const rfidBeamZ = rfidSensorZ - 0.52;
    const armLength = rfidSensorZ - armZ;
    box(0.58, 0.12, 0.58, rfidX, 0.12, armZ, '#536d7b');
    const armPost = new T.Mesh(
      new T.CylinderGeometry(0.09, 0.12, 3, 16),
      new T.MeshStandardMaterial({ color: '#718695', metalness: 0.78, roughness: 0.3 }),
    );
    armPost.position.set(rfidX, 1.56, armZ);
    armPost.castShadow = true;
    scene.add(armPost);
    box(0.14, 0.14, armLength, rfidX, 3.12, (armZ + rfidSensorZ) / 2, '#849aa6');
    const armJoint = new T.Mesh(
      new T.SphereGeometry(0.14, 16, 12),
      new T.MeshStandardMaterial({ color: '#d2a75f', metalness: 0.68, roughness: 0.3 }),
    );
    armJoint.position.set(rfidX, 3.12, armZ);
    armJoint.castShadow = true;
    scene.add(armJoint);
    box(0.4, 0.1, 0.32, rfidX, 3.19, rfidSensorZ, '#536d7b');
    box(0.32, 0.14, 0.24, rfidX, 3.07, rfidSensorZ, '#1d303e');
    const rfidLed = box(0.07, 0.06, 0.07, rfidX, 3.17, rfidSensorZ, '#56edb9');
    const rfidBeam = box(0.035, 0.42, 1.2, rfidX, 3.03, rfidBeamZ, '#39d6bc');
    const beamMaterial = rfidBeam.material as T.MeshStandardMaterial;
    beamMaterial.transparent = true;
    beamMaterial.opacity = 0.06;
    beamMaterial.emissive.set('#39d6bc');
    beamMaterial.emissiveIntensity = 0.3;
    const rfidLabel = text('RFID · PRONTO', rfidX, 3.42, rfidSensorZ + 0.13, 1.8, '#66f1cb');
    const displays: Record<string, (s: string) => void> = {};
    const lamps: Record<string, T.Mesh> = {};
    const conveyorCenter = conveyorLength / 2 - 0.5;
    const rollers = new T.CylinderGeometry(0.085, 0.085, 1.12, 12);
    const rollerMaterial = new T.MeshStandardMaterial({
      color: '#a3b7c6',
      roughness: 0.28,
      metalness: 0.78,
    });
    const conveyorRollers: T.Mesh[][] = [];
    for (const [x, label] of [
      [positions.IN, 'ENTRADA'],
      [positions.OUT, 'SAÍDA'],
    ] as const) {
      const beltRollers: T.Mesh[] = [];
      conveyorRollers.push(beltRollers);
      box(1.38, 0.22, conveyorLength, x, 0.52, conveyorCenter, '#243747');
      for (const side of [-1, 1]) {
        const rail = x + side * 0.66;
        box(0.13, 0.17, conveyorLength, rail, 0.72, conveyorCenter, '#d79a42');
        for (const z of [0.15, conveyorEnd / 3, (conveyorEnd * 2) / 3, conveyorEnd - 0.4]) {
          box(0.15, 0.68, 0.17, rail, 0.29, z, '#334a58');
        }
        box(0.14, 0.05, 0.77, rail, 0.83, 0, '#62e6c6');
      }
      for (let z = -0.36; z < conveyorLength - 0.55; z += 0.22) {
        const roller = new T.Mesh(rollers, rollerMaterial);
        roller.position.set(x, 0.685, z);
        roller.rotation.z = Math.PI / 2;
        roller.receiveShadow = true;
        scene.add(roller);
        beltRollers.push(roller);
      }
      text(label, x, 0.34, conveyorEnd + 0.2, 2.4);
    }
    Object.entries(positions).forEach(([name, x]) => {
      if (name === 'IN' || name === 'OUT') return;
      const qa = name === 'QA';
      const machine = qa || name.startsWith('M');
      const baseColor = qa ? '#44345e' : machine ? '#263b4e' : '#1d303e';
      box(machine ? stationWidth : bufferWidth, 0.65, machine ? 2.2 : 0.85, x, 0.35, 0, baseColor);
      box(machine ? 1.3 : 0.65, 0.09, 0.85, x, 0.73, 0, '#7b8c97');
      if (machine) {
        box(2.2, 1.8, 0.45, x, 1.3, -1.05, qa ? '#8064a9' : '#435e71');
        box(1.8, 0.6, 0.08, x, 1.6, -0.79, '#091b25');
        displays[name] = text('LIVRE', x, 1.65, -0.7, 1.7, qa ? '#e2caff' : '#66f1cb');
        text(name, x, 0.35, 1.3, 1.8);
        lamps[name] = box(0.16, 0.16, 0.18, x + 0.8, 2.35, -1, '#56edb9');
        for (let j = 0; j < 4; j++) box(0.5, 0.035, 0.06, x - 0.4, 1 + j * 0.12, -0.8, '#152c3c');
      } else text(name, x, 0.3, 1.15, 1.3);
    });
    text('ESTOQUE AUXILIAR', (positions.B1 + positions.B2) / 2, 0, 2.1, 3.5);
    text('AXION  /  NEXUS', centerX, -0.1, frontEdge + 0.2, 5, '#e2edf3');
    const meshes: Record<string, T.Mesh> = {};
    const labels: Record<string, T.Sprite> = {};
    function addUnit(u: State['units'][number]) {
      const mesh = box(0.52, 0.56, 0.52, 0, 1.05, 0, colors[u.product] ?? '#9ec4d4');
      mesh.userData.id = u.id;
      meshes[u.id] = mesh;
      labels[u.id] = text(u.id.slice(-3), 0, 0, 0, 0.65, '#ffffff').sprite;
    }
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
      const hit = ray.intersectObjects(Object.values(meshes).filter((mesh) => mesh.visible))[0];
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
          .multiplyScalar(Math.max(27, 39 / camera.aspect))
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
    let lastSession: string | undefined;
    let raf = 0,
      lastLabels = '',
      lastRfidLabel = 'RFID · PRONTO';
    const render = () => {
      const s = state.current;
      if (!dirty && lastTime === s.time && !s.live) {
        raf = requestAnimationFrame(render);
        return;
      }
      dirty = false;
      lastTime = s.time;
      const sameSession = lastSession === s.live?.session;
      lastSession = s.live?.session;
      const t = s.trip;
      const phaseTime = t
        ? Math.max(
            t.start,
            ...[
              t.approach,
              t.pickup,
              t.lifted,
              t.scanStart,
              t.scanEnd,
              t.arrived,
              t.drop,
              t.end,
            ].filter((time): time is number => time !== undefined && time <= s.time),
          )
        : s.time;
      const frame = reduced ? { ...s, time: phaseTime } : s;
      const p = s.live?.pose ?? pose(frame);
      const smooth = Boolean(s.live && sameSession && !reduced);
      const x = smooth ? T.MathUtils.lerp(carriage.position.x, p.x, 0.23) : p.x;
      const belt = conveyorProgress(frame);
      conveyorRollers[0].forEach((roller) => {
        roller.rotation.x = belt.input * 2 * Math.PI;
      });
      conveyorRollers[1].forEach((roller) => {
        roller.rotation.x = belt.output * 2 * Math.PI;
      });
      const input = s.units
        .filter((u) => u.location.startsWith('IN'))
        .sort((a, b) => a.location.localeCompare(b.location));
      const outputCount = s.units.filter((u) => u.location.startsWith('OUT')).length;
      carriage.position.x = x;
      screw.rotation.x = x * 8;
      const scannedUnit =
        s.trip?.scanStart !== undefined &&
        s.trip.scanEnd !== undefined &&
        s.time >= s.trip.scanStart &&
        s.time <= s.trip.scanEnd + 0.3
          ? s.units.find((u) => u.id === s.trip?.unit)
          : undefined;
      const readRfid = s.live?.rfid ?? scannedUnit?.id;
      const nextRfidLabel = readRfid ? `RFID · ${readRfid}` : 'RFID · PRONTO';
      if (nextRfidLabel !== lastRfidLabel) {
        lastRfidLabel = nextRfidLabel;
        rfidLabel(nextRfidLabel);
      }
      const rfidActive = Boolean(readRfid);
      const ledMaterial = rfidLed.material as T.MeshStandardMaterial;
      rfidLed.scale.setScalar(rfidActive ? 4 : 1);
      ledMaterial.color.set(rfidActive ? 'rgb(255, 0, 0)' : '#15fc00');
      ledMaterial.emissive.set(rfidActive ? '#fc0101' : '#001aff');
      ledMaterial.emissiveIntensity = rfidActive ? 1.4 : 0.4;
      beamMaterial.opacity = rfidActive ? 0.38 : 0.06;
      beamMaterial.emissiveIntensity = rfidActive ? 1.1 : 0.3;
      const y = smooth ? T.MathUtils.lerp(head.position.y, p.y, 0.23) : p.y;
      head.position.y = y;
      claws.forEach((c) => (c.position.y = y - 0.22));
      rod.position.y = (4.1 + y) / 2;
      rod.scale.y = (4.1 - y) / 2;
      const visibleUnits = new Set(s.units.map((u) => u.id));
      for (const id of Object.keys(meshes)) {
        const visible = visibleUnits.has(id);
        meshes[id].visible = labels[id].visible = visible;
      }
      for (const u of s.units) {
        const existing = meshes[u.id]?.visible;
        if (!meshes[u.id]) addUnit(u);
        const m = meshes[u.id];
        if (u.location === 'TRANS') {
          m.position.set(p.carrying ? x : positionX(s.trip!.to), p.carrying ? y - 0.38 : 1.05, 0);
        } else {
          const z = u.location.startsWith('IN')
            ? input.indexOf(u) + belt.input
            : u.location.startsWith('OUT')
              ? outputCount - 1 - Number(u.location.slice(3)) + belt.output
              : 0;
          const unitX = positionX(u.location);
          const unitZ = z * conveyorPitch;
          m.position.set(
            unitX,
            1.05,
            smooth && existing && m.position.x === unitX
              ? T.MathUtils.lerp(m.position.z, unitZ, 0.19)
              : unitZ,
          );
        }
        (m.material as T.MeshStandardMaterial).color.set(
          u.location.startsWith('OUT') && (!s.live || u.reviewed)
            ? u.rejected
              ? '#fa7983'
              : '#68e2ab'
            : (colors[u.product] ?? '#9ec4d4'),
        );
        labels[u.id].position.copy(m.position).add(new T.Vector3(0, 0.5, 0));
      }
      const labelKey = (s.live ? s.time : Math.floor(s.time * 5)).toString() + s.status;
      if (labelKey !== lastLabels) {
        lastLabels = labelKey;
        for (const name of Object.keys(displays)) {
          if (s.live) {
            const machine = s.live.machines[name];
            const remaining = machine?.tempo_restante_ms;
            displays[name](
              remaining != null
                ? `${(remaining / 1000).toFixed(1)}s`
                : (machine?.estado ?? 'livre').replaceAll('_', ' ').toUpperCase(),
            );
            (lamps[name].material as T.MeshStandardMaterial).color.set(
              remaining != null ? '#52f5bb' : machine?.estado === 'livre' ? '#607d8b' : '#ffc15b',
            );
            continue;
          }
          const u = s.units.find((u) => u.location === name);
          const remaining = u?.until === undefined ? null : Math.max(0, u.until - s.time);
          const stage = name === 'QA' ? 'QA' : `E${(u?.step ?? 0) + 1}`;
          const display =
            remaining !== null
              ? `${u?.product} · ${stage} · ${remaining.toFixed(1)}s`
              : u
                ? `${u.product} · AGUARDA`
                : 'LIVRE';
          displays[name](display);
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
