/* The catalogue remains usable even when a browser cannot create WebGL 2. */
(() => {
  'use strict';

  const byId = (id) => document.getElementById(id);
  const data = window.BURAN;
  const parts = new Map();
  const groups = new Map();
  const select = byId('parts');
  const state = { selected: null, isolated: false, exploded: false };
  const cameraButtons = Array.from(document.querySelectorAll('[data-command]'));
  const format = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 });
  let viewer = null;

  function measure(v) {
    return Array.isArray(v) && v.length === 3 && v.every(Number.isFinite)
      ? `${v.map((n) => format.format(n)).join(' × ')} мм`
      : '';
  }

  function render() {
    const item = parts.get(state.selected);
    byId('assembled').setAttribute('aria-pressed', String(!state.exploded));
    byId('exploded').setAttribute('aria-pressed', String(state.exploded));
    const view = state.isolated ? 'Отдельно' : state.exploded ? 'Разнесение' : 'Общий вид';
    byId('scene-caption').textContent = item ? `${view} · ${item.label}` : view;
    byId('part-card').hidden = !item;
    select.value = item?.id || '';
    if (!item) return;
    byId('part-code').textContent =
      `Поз. ${String(item.index + 1).padStart(2, '0')} / ${item.group || 'Деталь'}`;
    byId('part-name').textContent = item.label;
    byId('part-note').textContent = item.note || '';
    const sizes = [];
    if (measure(item.size)) sizes.push(`В сборке: ${measure(item.size)}`);
    if (measure(item.printSize)) sizes.push(`В печати: ${measure(item.printSize)}`);
    byId('part-size').textContent = sizes.join(' · ');
    byId('isolate').disabled = !viewer;
    byId('isolate').setAttribute('aria-pressed', String(state.isolated));
    byId('isolate').textContent = state.isolated ? 'Вернуть остальные' : 'Показать отдельно';
    const stl = byId('part-download');
    // Accept only the supplied local printable artefact, on file: and on Pages.
    stl.hidden = !/^files\/stl\/[^/\\?#]+\.stl$/iu.test(item.stl);
    if (!stl.hidden) stl.setAttribute('href', item.stl);
    else stl.removeAttribute('href');
  }

  function choose(id, source) {
    state.selected = parts.has(id) ? id : null;
    if (!state.selected) state.isolated = false;
    viewer?.select(state.selected, state.isolated);
    render();
    if (source === 'scene' && state.selected) {
      byId('notice').textContent = `Выбрано: ${parts.get(id).label}. Карточка открыта под моделью.`;
    }
  }

  function mode(exploded) {
    // The two positions always address the assembly, including after isolating a part.
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

  function cameraEnabled(enabled) {
    const buttons = [...cameraButtons, byId('assembled'), byId('exploded'), byId('isolate')];
    for (const button of buttons) button.disabled = !enabled;
  }

  function sceneError(message) {
    viewer = null;
    byId('scene-error').textContent = message;
    byId('scene-error').hidden = false;
    byId('gesture').hidden = true;
    cameraEnabled(false);
  }

  function populate() {
    if (!Array.isArray(data?.parts) || !data.parts.length) {
      sceneError(
        'Не найден каталог модели. При открытии с диска сохраните папку site целиком, включая assets и vendor.',
      );
      return false;
    }
    for (const [index, original] of data.parts.entries()) {
      const item = { ...original, index };
      parts.set(item.id, item);
      const group = item.group || 'Детали';
      if (!groups.has(group)) {
        const optgroup = document.createElement('optgroup');
        optgroup.label = group;
        groups.set(group, optgroup);
        select.append(optgroup);
      }
      groups
        .get(group)
        .append(new Option(`${String(index + 1).padStart(2, '0')} · ${item.label}`, item.id));
    }
    select.disabled = false;
    byId('scene-scale').textContent = `М ${data.scale}`;
    byId('scene-scale').hidden = !data.scale;
    byId('scale').textContent = data.scale || '—';
    byId('size').textContent = measure(data.dimensions) || '—';
    byId('orbiter').textContent = measure(data.orbiter) || '—';
    byId('part-count').textContent = String(parts.size);
    if (measure(data.printer)) byId('printer').textContent = ` (область ${measure(data.printer)})`;
    return true;
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
  for (const button of cameraButtons) {
    button.addEventListener('click', () => {
      const action = button.dataset.command;
      if (action === 'reset') reset();
      else viewer?.zoom(action === 'in' ? 1.25 : 0.8);
    });
  }

  async function open() {
    if (!populate()) return;
    try {
      viewer = await window.BuranViewport.create(byId('model'), data, {
        pick: (id) => choose(id, 'scene'),
        reset,
        error: sceneError,
      });
      cameraEnabled(true);
      viewer.select(state.selected, false);
      render();
    } catch (error) {
      console.error('БТС-001:', error);
      sceneError(error.message || 'Не удалось открыть 3D. Каталог и файлы доступны ниже.');
    }
  }
  open();
})();
