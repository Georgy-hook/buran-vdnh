/* Studio and framing math for the exhibition. All positions are in metres. */
(() => {
  'use strict';

  function lightTent(T) {
    const w = 128;
    const h = 64;
    const pixels = new Float32Array(w * h * 4);
    const panels = [
      { axis: [-0.6, 0.9, 0.3], power: 12, strength: 3.6 },
      { axis: [0.5, 0.5, -1], power: 17, strength: 3 },
      { axis: [0.8, 0.1, 0.7], power: 9, strength: 1.2 },
    ];
    for (const panel of panels) {
      panel.direction = new T.Vector3(...panel.axis).normalize();
    }
    const normal = new T.Vector3();
    for (let row = 0; row < h; row++) {
      const lat = (row / h - 0.5) * Math.PI;
      for (let col = 0; col < w; col++) {
        const lon = (col / w - 0.5) * Math.PI * 2;
        normal.set(Math.cos(lat) * Math.cos(lon), Math.sin(lat), Math.cos(lat) * Math.sin(lon));
        let light = 0.16 + 0.1 * (normal.y + 1);
        for (const panel of panels) {
          light += panel.strength * Math.max(0, normal.dot(panel.direction)) ** panel.power;
        }
        const i = 4 * (row * w + col);
        pixels[i] = light;
        pixels[i + 1] = light * 0.99;
        pixels[i + 2] = light * 0.965;
        pixels[i + 3] = 1;
      }
    }
    const texture = new T.DataTexture(pixels, w, h, T.RGBAFormat, T.FloatType);
    texture.mapping = T.EquirectangularReflectionMapping;
    texture.colorSpace = T.LinearSRGBColorSpace;
    texture.needsUpdate = true;
    return texture;
  }

  function illuminate(T, renderer, scene) {
    scene.environment = lightTent(T);
    scene.environmentIntensity = 0.74;
    const dome = new T.HemisphereLight(0xfffbf4, 0xa5b4bc, 0.92);
    const key = new T.DirectionalLight(0xfff8ed, 2.05);
    const edge = new T.DirectionalLight(0xd0e9ff, 1.65);
    const keyDirection = new T.Vector3(-0.9, 1.85, 0.75).normalize();
    key.castShadow = true;
    key.shadow.mapSize.set(1024, 1024);
    key.shadow.bias = -0.00025;
    const floor = new T.Mesh(
      new T.PlaneGeometry(1, 1),
      new T.ShadowMaterial({ color: 0x0a1718, opacity: 0.25, depthWrite: false }),
    );
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = T.PCFShadowMap;
    renderer.shadowMap.autoUpdate = false;
    scene.add(dome, key, key.target, edge, edge.target, floor);

    return function place(box, center, radius, contact) {
      floor.visible = contact;
      floor.scale.setScalar(radius * 10);
      floor.position.set(center.x, box.min.y - radius * 0.002, center.z);
      key.target.position.copy(center);
      edge.target.position.copy(center);
      edge.position.copy(center).addScaledVector(new T.Vector3(0.8, 1, -1), radius * 4);
      key.position.copy(center).addScaledVector(keyDirection, radius * 4);
      const half = radius * 1.5;
      Object.assign(key.shadow.camera, {
        left: -half,
        right: half,
        top: half,
        bottom: -half,
        near: radius * 0.1,
        far: radius * 8,
      });
      key.shadow.camera.updateProjectionMatrix();
      renderer.shadowMap.needsUpdate = true;
    };
  }

  // Preserve a compact set of actual surface points, not empty corners of a
  // wing's rectangular box. This keeps a long, swept silhouette large on screen.
  function supportPoints(T, surfaces) {
    const axes = [];
    for (let a = 0; a < 8; a++) {
      for (const rise of [-1, 0, 1]) {
        axes.push(new T.Vector3(Math.cos((a * Math.PI) / 4), rise, Math.sin((a * Math.PI) / 4)));
      }
    }
    axes.push(new T.Vector3(0, 1, 0), new T.Vector3(0, -1, 0));
    const best = axes.map(() => -Infinity);
    const points = axes.map(() => new T.Vector3());
    const p = new T.Vector3();
    for (const mesh of surfaces) {
      const attr = mesh.geometry.attributes.position;
      const step = Math.max(1, Math.ceil(attr.count / 5000));
      for (let i = 0; i < attr.count; i += step) {
        p.fromBufferAttribute(attr, i).applyMatrix4(mesh.matrixWorld);
        axes.forEach((axis, j) => {
          const dot = p.dot(axis);
          if (dot > best[j]) {
            best[j] = dot;
            points[j].copy(p);
          }
        });
      }
    }
    return points;
  }

  function framing(T, parts, aspect, fov, eye, isolated, amount) {
    const cloud = [];
    const bounds = new T.Box3();
    for (const part of parts.values()) {
      if (isolated && isolated !== part.id) continue;
      const delta = part.delta.clone().multiplyScalar(amount);
      bounds.union(part.bounds.clone().translate(delta));
      for (const point of part.points) cloud.push(point.clone().add(delta));
    }
    const right = new T.Vector3().crossVectors(new T.Vector3(0, 1, 0), eye).normalize();
    const up = new T.Vector3().crossVectors(eye, right);
    // Center the visible silhouette in the image plane even for an asymmetric model.
    const image = new T.Box3();
    for (const p of cloud) image.expandByPoint(new T.Vector3(p.dot(right), p.dot(up), p.dot(eye)));
    const mid = image.getCenter(new T.Vector3());
    const center = right
      .clone()
      .multiplyScalar(mid.x)
      .addScaledVector(up, mid.y)
      .addScaledVector(eye, mid.z);
    const radius = Math.max(0.00001, bounds.getSize(new T.Vector3()).length() / 2);
    const slopeY = Math.tan((fov * Math.PI) / 360);
    let distance = radius * 0.42;
    for (const p of cloud) {
      const relative = p.sub(center);
      const depth = relative.dot(eye);
      distance = Math.max(
        distance,
        depth + Math.abs(relative.dot(right)) / (slopeY * aspect * 0.87),
        depth + Math.abs(relative.dot(up)) / (slopeY * 0.84),
      );
    }
    return { center, distance, bounds, radius };
  }

  window.BuranStudio = Object.freeze({ illuminate, supportPoints, framing });
})();
