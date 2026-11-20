/* Classic scripts + embedded GLB: no model fetch, Blob module import or CDN. */
(() => {
  'use strict';

  async function parse(T, encoded) {
    if (!encoded) throw new Error('Не найдены данные геометрии.');
    let bytes;
    if (typeof Uint8Array.fromBase64 === 'function') {
      bytes = Uint8Array.fromBase64(encoded);
    } else {
      const binary = atob(encoded);
      bytes = Uint8Array.from(binary, (ch) => ch.charCodeAt(0));
    }
    const head = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    if (
      bytes.length < 20 ||
      head.getUint32(0, true) !== 0x46546c67 ||
      head.getUint32(4, true) !== 2 ||
      head.getUint32(8, true) !== bytes.length
    ) {
      throw new Error('Файл геометрии повреждён.');
    }
    const manager = new T.LoadingManager();
    manager.setURLModifier((url) => {
      if (/^(data|blob):/i.test(url)) return url;
      throw new Error('Модель содержит внешнюю зависимость.');
    });
    return new T.GLTFLoader(manager).parseAsync(bytes.buffer, '');
  }

  function register(T, scene, gltf, catalog) {
    const root = gltf.scene;
    const nodes = new Map();
    const parts = new Map();
    const owners = new WeakMap();
    scene.add(root);
    root.traverse((obj) => {
      const index = gltf.parser.associations.get(obj)?.nodes;
      const id = gltf.parser.json.nodes[index]?.name;
      if (id) nodes.set(id, obj);
    });
    // Put each physical item directly in the world frame before applying its
    // world-space explosion vector. attach() preserves its assembled transform.
    for (const item of catalog) {
      const node = nodes.get(item.id);
      if (!node) throw new Error(`В геометрии нет детали «${item.label}».`);
      scene.attach(node);
      parts.set(item.id, {
        id: item.id,
        node,
        origin: node.position.clone(),
        delta: new T.Vector3(...item.explode),
        surfaces: [],
      });
    }
    scene.remove(root);
    scene.updateMatrixWorld(true);
    for (const part of parts.values()) {
      part.node.traverse((mesh) => {
        if (!mesh.isMesh) return;
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        owners.set(mesh, part.id);
        part.surfaces.push(mesh);
      });
      if (!part.surfaces.length) throw new Error('В одной из деталей отсутствуют поверхности.');
      part.bounds = new T.Box3().setFromObject(part.node);
      part.points = window.BuranStudio.supportPoints(T, part.surfaces);
    }
    return { parts, owners };
  }

  function bindPicking(canvas, pick, settle) {
    const contacts = new Set();
    let tap = null;
    function move(e) {
      if (tap?.id === e.pointerId && Math.hypot(e.clientX - tap.x, e.clientY - tap.y) > 5)
        tap = null;
    }
    canvas.addEventListener(
      'pointerdown',
      (e) => {
        settle();
        contacts.add(e.pointerId);
        tap =
          contacts.size === 1 && e.isPrimary && e.button === 0
            ? { id: e.pointerId, x: e.clientX, y: e.clientY }
            : null;
      },
      true,
    );
    canvas.addEventListener('pointermove', move, true);
    canvas.addEventListener(
      'pointerup',
      (e) => {
        move(e);
        const hit = tap?.id === e.pointerId;
        contacts.delete(e.pointerId);
        tap = null;
        if (hit) pick(e);
      },
      true,
    );
    for (const name of ['pointercancel', 'lostpointercapture']) {
      canvas.addEventListener(
        name,
        (e) => {
          contacts.delete(e.pointerId);
          tap = null;
        },
        true,
      );
    }
    canvas.addEventListener('wheel', settle, { capture: true, passive: true });
  }

  async function create(canvas, data, events) {
    const T = window.AtlasThree;
    if (!T) throw new Error('Не найдена локальная библиотека 3D.');
    const gltf = await parse(T, data.glb);
    const scene = new T.Scene();
    const { parts, owners } = register(T, scene, gltf, data.parts);
    let renderer;
    try {
      renderer = new T.WebGLRenderer({ canvas, antialias: true, alpha: true });
    } catch {
      throw new Error('Для осмотра нужен WebGL 2. Детали и файлы доступны ниже.');
    }
    renderer.setClearColor(0, 0);
    renderer.outputColorSpace = T.SRGBColorSpace;
    renderer.toneMapping = T.NeutralToneMapping;
    renderer.toneMappingExposure = 1.0;
    const light = window.BuranStudio.illuminate(T, renderer, scene);
    const camera = new T.PerspectiveCamera(32, 1, 0.0001, 10);
    const home = new T.Vector3(-0.90, 0.93, 1.10).normalize();
    const orbit = new T.OrbitControls(camera, canvas);
    orbit.enablePan = false;
    orbit.enableDamping = false;
    orbit.rotateSpeed = 0.7;
    orbit.minPolarAngle = 0.015;
    orbit.maxPolarAngle = Math.PI - 0.015;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    const ray = new T.Raycaster();
    const pointer = new T.Vector2();
    const originals = new Map();
    const highlights = new Map();
    let selected = null;
    let isolated = null;
    let amount = 0;
    let destination = 0;
    let anim = null;
    let pending = 0;
    let width = 0;
    let height = 0;
    let lost = false;

    const currentEye = () => camera.position.clone().sub(orbit.target).normalize();
    function frame(eye, value) {
      return window.BuranStudio.framing(T, parts, camera.aspect, camera.fov, eye, isolated, value);
    }
    function placeCamera(center, eye, distance) {
      orbit.target.copy(center);
      camera.position.copy(center).addScaledVector(eye, distance);
      orbit.update();
    }
    function placeParts(value) {
      amount = value;
      for (const part of parts.values()) {
        part.node.position.copy(part.origin).addScaledVector(part.delta, value);
        part.node.visible = !isolated || part.id === isolated;
      }
    }
    function setRange(fit) {
      orbit.minDistance = Math.max(0.000002, fit.radius * 0.15);
      orbit.maxDistance = fit.distance * 6;
      camera.near = Math.max(0.0000001, fit.radius * 0.002);
      camera.far = Math.max(fit.radius * 35, orbit.maxDistance * 2);
      camera.updateProjectionMatrix();
    }
    function snap(eye = currentEye()) {
      anim = null;
      placeParts(destination);
      const fit = frame(eye, destination);
      setRange(fit);
      placeCamera(fit.center, eye, fit.distance);
      light(fit.bounds, fit.center, fit.radius, destination === 0 || !!isolated);
      dirty();
    }
    function settle() {
      if (anim) snap(anim.eye);
    }
    function draw(now) {
      pending = 0;
      if (lost || !width || !height) return;
      if (anim) {
        const t = Math.min(1, (now - anim.start) / 360);
        const ease = t * t * (3 - 2 * t);
        placeParts(anim.from + (destination - anim.from) * ease);
        const center = anim.center.clone().lerp(anim.fit.center, ease);
        placeCamera(center, anim.eye, anim.dist + (anim.fit.distance - anim.dist) * ease);
        renderer.shadowMap.needsUpdate = true;
        if (t === 1) snap(anim.eye);
        else dirty();
      }
      renderer.render(scene, camera);
    }
    function dirty() {
      if (!pending && !lost) pending = requestAnimationFrame(draw);
    }
    orbit.addEventListener('change', dirty);

    function explode(value) {
      destination = value ? 1 : 0;
      if (reduced.matches || isolated) {
        snap();
        return;
      }
      const eye = currentEye();
      const fit = frame(eye, destination);
      const dist = camera.position.distanceTo(orbit.target);
      setRange(fit);
      light(fit.bounds, fit.center, fit.radius, false);
      anim = {
        eye,
        fit,
        center: orbit.target.clone(),
        dist,
        from: amount,
        start: performance.now(),
      };
      dirty();
    }
    function highlight(material) {
      if (highlights.has(material)) return highlights.get(material);
      const copy = material.clone();
      if (copy.emissive) {
        copy.emissive.set(0xe4753b);
        copy.emissiveIntensity = 0.32;
      } else {
        copy.color?.lerp(new T.Color(0xf89255), 0.45);
      }
      highlights.set(material, copy);
      return copy;
    }
    function select(id, solo) {
      for (const [mesh, material] of originals) mesh.material = material;
      originals.clear();
      selected = parts.has(id) ? id : null;
      const next = solo ? selected : null;
      if (next !== isolated) {
        isolated = next;
        snap();
      }
      if (selected && !isolated) {
        for (const mesh of parts.get(selected).surfaces) {
          originals.set(mesh, mesh.material);
          mesh.material = Array.isArray(mesh.material)
            ? mesh.material.map(highlight)
            : highlight(mesh.material);
        }
      }
      dirty();
    }
    function pick(event) {
      const rect = canvas.getBoundingClientRect();
      pointer.set(
        (2 * (event.clientX - rect.left)) / rect.width - 1,
        1 - (2 * (event.clientY - rect.top)) / rect.height,
      );
      camera.updateMatrixWorld();
      scene.updateMatrixWorld(true);
      ray.setFromCamera(pointer, camera);
      const surfaces = [];
      for (const part of parts.values()) {
        if (part.node.visible) surfaces.push(...part.surfaces);
      }
      const hit = ray.intersectObjects(surfaces, false)[0];
      if (hit) events.pick(owners.get(hit.object));
    }
    function zoom(factor) {
      settle();
      const distance = camera.position.distanceTo(orbit.target) / factor;
      placeCamera(
        orbit.target,
        currentEye(),
        Math.max(orbit.minDistance, Math.min(orbit.maxDistance, distance)),
      );
      dirty();
    }
    function resize() {
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      if (!w || !h || (w === width && h === height)) return;
      const first = !width;
      width = w;
      height = h;
      renderer.setPixelRatio(
        Math.min(window.devicePixelRatio || 1, 2, Math.sqrt(2500000 / (w * h))),
      );
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      snap(first ? home : currentEye());
    }
    bindPicking(canvas, pick, settle);
    canvas.addEventListener('keydown', (event) => {
      if (event.altKey || event.metaKey || event.ctrlKey) return;
      const key = event.key;
      if (key === 'Home') events.reset();
      else if (key === '+' || key === '=') zoom(1.2);
      else if (key === '-') zoom(1 / 1.2);
      else if (key.startsWith('Arrow')) {
        settle();
        const theta =
          orbit.getAzimuthalAngle() +
          (key === 'ArrowRight' ? 0.13 : key === 'ArrowLeft' ? -0.13 : 0);
        const phi = Math.min(
          orbit.maxPolarAngle,
          Math.max(
            orbit.minPolarAngle,
            orbit.getPolarAngle() + (key === 'ArrowUp' ? -0.13 : key === 'ArrowDown' ? 0.13 : 0),
          ),
        );
        const eye = new T.Vector3().setFromSphericalCoords(1, phi, theta);
        placeCamera(orbit.target, eye, camera.position.distanceTo(orbit.target));
      } else return;
      event.preventDefault();
    });
    canvas.addEventListener('webglcontextlost', (event) => {
      event.preventDefault();
      lost = true;
      events.error('Контекст 3D потерян. Перезагрузите страницу для повторного осмотра.');
    });
    new ResizeObserver(resize).observe(canvas);
    resize();
    return {
      select,
      explode,
      zoom,
      reset() {
        destination = 0;
        select(null, false);
        snap(home);
      },
    };
  }

  window.BuranViewport = Object.freeze({ create });
})();
