/* Classic scripts keep the local catalogue and the opt-in viewer usable on file://. */
(() => {
  'use strict';

  const byId = (id) => document.getElementById(id);
  const select = byId('parts');
  const canvas = byId('model');
  const toggle = byId('open-model');
  const caption = toggle.querySelector('span');
  const controls = byId('model-tools');
  const tools = byId('camera-tools');
  const error = byId('scene-error');
  const poster = byId('poster');
  const parts = new Map();
  const scripts = new Map();
  const state = { selected: null, isolated: false, exploded: false };
  const format = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 });
  let viewer = null;
  let loading = false;
  let lost = false;

  function measure(v) {
    return Array.isArray(v) && v.length === 3 && v.every(Number.isFinite)
      ? `${v.map((n) => format.format(n)).join(' × ')} мм`
      : '';
  }

  function populate(data) {
    if (!data?.parts?.length || parts.size) return;
    const groups = new Map();
    for (const item of data.parts) {
      parts.set(item.id, item);
      const group = item.group || 'Детали';
      if (!groups.has(group)) {
        const optgroup = document.createElement('optgroup');
        optgroup.label = group;
        groups.set(group, optgroup);
        select.append(optgroup);
      }
      groups.get(group).append(new Option(item.label, item.id));
    }
    for (const [id, text] of Object.entries({
      scale: data.scale,
      size: measure(data.dimensions),
      orbiter: measure(data.orbiter),
      printer: measure(data.printer),
    })) {
      if (text) byId(id).textContent = text;
    }
    const ar = byId('quick-look');
    if (data === window.BURAN_CATALOG && data.quickLook === 'files/Buran.usdz') {
      if (ar.relList.supports?.('ar')) {
        ar.href = data.quickLook;
        byId('ar-option').hidden = false;
      } else {
        const usdz = byId('usdz-download');
        usdz.href = data.quickLook;
        usdz.hidden = false;
      }
    }
  }

  function render() {
    const item = parts.get(state.selected);
    byId('assembled').setAttribute('aria-pressed', String(!state.exploded));
    byId('exploded').setAttribute('aria-pressed', String(state.exploded));
    byId('part-card').hidden = !item;
    select.value = item?.id || '';
    if (!item) return;
    byId('part-name').textContent = item.label;
    byId('part-note').textContent = item.note || '';
    const sizes = [];
    if (measure(item.size)) sizes.push(`В сборке: ${measure(item.size)}.`);
    if (measure(item.printSize)) sizes.push(`В печати: ${measure(item.printSize)}.`);
    byId('part-size').textContent = sizes.join(' ');
    byId('isolate').setAttribute('aria-pressed', String(state.isolated));
    byId('isolate').textContent = state.isolated ? 'Вернуть остальные' : 'Показать отдельно';
    const stl = byId('part-download');
    stl.hidden = !/^files\/stl\/[^/\\?#]+\.stl$/iu.test(item.stl);
    if (!stl.hidden) stl.setAttribute('href', item.stl);
    else stl.removeAttribute('href');
  }

  function choose(id, source) {
    state.selected = parts.has(id) ? id : null;
    if (!state.selected) state.isolated = false;
    viewer?.select(state.selected, state.isolated);
    render();
    if (source === 'scene' && state.selected)
      byId('notice').textContent = `Выбрано: ${parts.get(id).label}. Описание под моделью.`;
  }

  function mode(exploded) {
    if (state.isolated) {
      state.isolated = false;
      viewer?.select(state.selected, false);
    }
    state.exploded = exploded;
    viewer?.explode(exploded);
    render();
  }

  function reset() {
    state.selected = null;
    state.exploded = false;
    state.isolated = false;
    viewer?.reset();
    render();
    byId('notice').textContent = 'Восстановлен общий вид собранной модели.';
  }

  function showScene(active) {
    canvas.hidden = !active;
    poster.hidden = active;
    tools.hidden = !active;
    controls.hidden = !active;
    caption.textContent = active ? 'Закрыть 3D' : 'Вращать в 3D';
    toggle.setAttribute('aria-expanded', String(active));
    if (active) canvas.focus({ preventScroll: true });
  }

  function sceneError(message) {
    showScene(false);
    // Keep the catalogue, individual STL links and dimensions available without WebGL.
    if (parts.size) controls.hidden = false;
    for (const id of ['isolate', 'assembled', 'exploded']) byId(id).disabled = true;
    byId('gesture').hidden = true;
    error.textContent = message;
    error.hidden = false;
  }

  function loadScript(src) {
    if (!scripts.has(src)) {
      scripts.set(
        src,
        new Promise((resolve, reject) => {
          const script = document.createElement('script');
          script.src = src;
          script.onload = resolve;
          script.onerror = () => {
            scripts.delete(src);
            script.remove();
            reject(
              new Error(
                'Не удалось загрузить файлы 3D. При открытии с диска сохраните папку site целиком.',
              ),
            );
          };
          document.head.append(script);
        }),
      );
    }
    return scripts.get(src);
  }

  select.addEventListener('change', () => choose(select.value, 'list'));
  byId('isolate').addEventListener('click', () => {
    if (!viewer || !state.selected) return;
    state.isolated = !state.isolated;
    viewer.select(state.selected, state.isolated);
    render();
  });
  byId('assembled').addEventListener('click', () => mode(false));
  byId('exploded').addEventListener('click', () => mode(true));
  for (const button of document.querySelectorAll('[data-command]')) {
    button.addEventListener('click', () => {
      const action = button.dataset.command;
      if (action === 'reset') reset();
      else viewer?.zoom(action === 'in' ? 1.25 : 0.8);
    });
  }

  toggle.addEventListener('click', async () => {
    if (loading || lost) return;
    if (viewer) {
      showScene(canvas.hidden);
      return;
    }
    loading = true;
    toggle.disabled = true;
    toggle.setAttribute('aria-busy', 'true');
    caption.textContent = 'Открываем 3D…';
    error.hidden = true;
    try {
      // These scripts only declare globals: dependencies are used after all four finish.
      await Promise.all(
        ['vendor/three-atlas.js', 'assets/model-data.js', 'studio.js', 'viewport.js'].map(
          loadScript,
        ),
      );
      populate(window.BURAN);
      canvas.hidden = false;
      // Keep the poster on top while creating the WebGL context at the final canvas size.
      canvas.style.visibility = 'hidden';
      viewer = await window.BuranViewport.create(canvas, window.BURAN, {
        pick: (id) => choose(id, 'scene'),
        reset,
        error(message) {
          lost = true;
          toggle.disabled = true;
          sceneError(message);
        },
      });
      for (const id of ['isolate', 'assembled', 'exploded']) byId(id).disabled = false;
      byId('gesture').hidden = false;
      viewer.select(state.selected, state.isolated);
      render();
      showScene(true);
    } catch (reason) {
      sceneError(
        reason.message || 'Не удалось открыть 3D. Файлы для печати доступны в мастерской.',
      );
    } finally {
      canvas.style.removeProperty('visibility');
      if (!canvas.hidden) canvas.focus({ preventScroll: true });
      toggle.removeAttribute('aria-busy');
      toggle.disabled = lost;
      loading = false;
    }
  });

  populate(window.BURAN_CATALOG);
  toggle.hidden = false;
})();
