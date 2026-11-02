<script>
window.dash = (() => {
  const DATA = window.__DATA, calcs = {}, cache = {}, draws = {};
  const data = (id) => {
    if (cache[id]) return cache[id];
    if (DATA[id]) return (cache[id] = {status: 'ok', data: DATA[id]});
    const c = calcs[id];
    if (c) { try { return (cache[id] = {status: 'ok', data: c.fn(...c.inputs.map((i) => data(i).data))}); } catch (e) { console.error(id, e); return {status: 'error', data: []}; } }
    return {status: 'missing', data: []};
  };
  const run = (name) => document.querySelectorAll('[data-draw="' + name + '"]').forEach((el) => { try { draws[name](el); } catch (e) { console.error(name, e); } });
  const api = {
    data, calc: (id, o) => { calcs[id] = o; },
    draw: (name, fn) => { if (fn) { draws[name] = fn; } else if (draws[name]) run(name); },
    onData: (fn) => fn(), setLink: (n) => { try { history.replaceState(null, '', n ? '#' + n : location.pathname); } catch (e) {} },
    _runAll: () => Object.keys(draws).forEach(run)
  };
  return api;
})();
</script>
