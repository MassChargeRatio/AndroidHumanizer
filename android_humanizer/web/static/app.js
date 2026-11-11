'use strict';

/* =========================================================
   android-humanizer Web UI frontend logic.
   Zero framework, zero CDN.

   android-humanizer Web UI 前端逻辑。
   零框架、零 CDN。
   ========================================================= */

// ---------------------------------------------------------- query helpers

const $ = s => document.querySelector(s);
const $$ = s => Array.from(document.querySelectorAll(s));

// Line colors for the sensor chart.
// 传感器图表的曲线颜色。
const COLORS = {
  acc_x: '#4c8dff', acc_y: '#2fbf71', acc_z: '#e2a33c',
  gyro_x: '#c08bff', gyro_y: '#e5534b', gyro_z: '#5f9ea0',
};

// ---------------------------------------------------------- tabs

// Tab switching: one <section class="tab"> per view.
// Tab 切换：每个视图对应一个 <section class="tab">。
$$('nav.tabs button').forEach(btn => {
  btn.addEventListener('click', () => {
    $$('nav.tabs button').forEach(b => b.classList.toggle('on', b === btn));
    $$('section.tab').forEach(s => {
      s.classList.toggle('on', s.id === 'tab-' + btn.dataset.tab);
    });
  });
});

// ---------------------------------------------------------- HTTP

// POST JSON and throw on non-ok responses.
// 发送 JSON POST 请求；非 ok 响应抛错。
async function postJSON(path, body) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({ ok: false, error: 'HTTP ' + res.status }));
  if (!data.ok) throw new Error(data.error || ('HTTP ' + res.status));
  return data;
}

// Read the seed input; empty string -> null (random).
// 读取 seed 输入；空串 -> null（随机）。
function seedOf(el) {
  const v = el.value.trim();
  return v === '' ? null : Number(v);
}

// ---------------------------------------------------------- language
// ---------------------------------------------------------- 语言切换
//
// Current UI language ('zh' | 'en'), persisted in localStorage.
// Static copy: <span class="zh"> / <span class="en"> toggled by
// body[data-lang] CSS. Dynamic copy: t(zh, en).
// 当前 UI 语言（'zh' | 'en'），localStorage 持久化。静态文案由
// body[data-lang] 的 CSS 控制 zh/en 显隐；动态文案用 t(zh, en)。
let LANG = localStorage.getItem('th-lang') || 'zh';

function t(zh, en) {
  return LANG === 'en' ? en : zh;
}

function applyLang() {
  document.body.dataset.lang = LANG;
  document.querySelectorAll('[data-ph-zh]').forEach(el => {
    el.placeholder = LANG === 'en' ? el.dataset.phEn : el.dataset.phZh;
  });
  const sel = $('#lang');
  if (sel) sel.value = LANG;
  // Re-render every dynamic section with the current data.
  // 用当前数据重渲染所有动态区。
  generateGesture();
  sampleTiming();
  calcWindow();
  simulateCooldown();
  generateSensors();
}

$('#lang').addEventListener('change', e => {
  LANG = e.target.value;
  localStorage.setItem('th-lang', LANG);
  applyLang();
});

// ========================================================== kinematics

let lastGesture = null;
let playTimer = null;

// Collect all kinematics form values into a request body.
// 收集 kinematics 表单全部字段为请求体。
function kBody() {
  return {
    start: [Number($('#kx0').value), Number($('#ky0').value)],
    end: [Number($('#kx1').value), Number($('#ky1').value)],
    seed: seedOf($('#kseed')),
    for_slider: $('#kslider').checked,
    exact_end: $('#kexact').checked,
    enabled: $('#k_enabled').checked,
    // Advanced params.
    // 高级参数。
    steps_min: Number($('#k_steps_min').value),
    steps_max: Number($('#k_steps_max').value),
    px_per_step: Number($('#k_px_per_step').value),
    duration_per_px: Number($('#k_duration_per_px').value),
    duration_min: Number($('#k_duration_min').value),
    duration_max: Number($('#k_duration_max').value),
    perpendicular_ratio: Number($('#k_perp').value),
    jitter_sigma: Number($('#k_jitter').value),
    jitter_tail_fraction: Number($('#k_jtail').value),
    overshoot_prob: Number($('#k_overshoot').value),
    overshoot_ratio: Number($('#k_oratio').value),
    use_ease_in_out: $('#k_ease').checked,
  };
}

// Request a gesture and redraw.
// 请求轨迹并重绘。
async function generateGesture() {
  try {
    const data = await postJSON('/api/gesture', kBody());
    lastGesture = data.gesture;
    drawKinematics(lastGesture);
    const g = lastGesture;
    $('#kmeta').innerHTML =
      `${t('点数', 'points')} <b>${g.steps}</b><br>${t('距离', 'distance')} <b>${g.distance.toFixed(1)}</b> px<br>` +
      `${t('时长', 'duration')} <b>${g.duration.toFixed(3)}</b> s<br>` +
      `${t('滑块模式', 'slider')} ${g.for_slider ? t('是', 'yes') : t('否', 'no')}<br>` +
      `${t('首点', 'first')} (${g.points[0].join(', ')})<br>${t('末点', 'last')} (${g.points[g.points.length - 1].join(', ')})`;
    $('#kplay-status').textContent = '';
  } catch (e) {
    $('#kmeta').textContent = t('错误', 'Error') + ': ' + e.message;
  }
}

// Draw the trajectory on canvas; cursorIdx limits how many points to render.
// 在 canvas 上绘制轨迹；cursorIdx 控制渲染到第几个点（用于动画）。
function drawKinematics(g, cursorIdx) {
  const cv = $('#cv-kinematics');
  const ctx = cv.getContext('2d');
  ctx.clearRect(0, 0, cv.width, cv.height);
  ctx.fillStyle = '#0e1116';
  ctx.fillRect(0, 0, cv.width, cv.height);

  const pts = g.points;
  if (!pts.length) return;

  // Auto-fit points into canvas.
  // 自动缩放点集到画布。
  const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
  const pad = 30;
  const minX = Math.min(...xs) - pad, maxX = Math.max(...xs) + pad;
  const minY = Math.min(...ys) - pad, maxY = Math.max(...ys) + pad;
  const w = maxX - minX || 1, h = maxY - minY || 1;
  const scale = Math.min((cv.width - 2 * pad) / w, (cv.height - 2 * pad) / h);
  const ox = pad + (cv.width - 2 * pad - w * scale) / 2;
  const oy = pad + (cv.height - 2 * pad - h * scale) / 2;
  const tx = x => ox + (x - minX) * scale;
  const ty = y => oy + (y - minY) * scale;

  // Path.
  // 轨迹线。
  ctx.strokeStyle = '#4c8dff';
  ctx.lineWidth = 2;
  ctx.beginPath();
  const limit = cursorIdx === undefined ? pts.length : cursorIdx + 1;
  for (let i = 0; i < limit; i++) {
    const X = tx(pts[i][0]), Y = ty(pts[i][1]);
    i ? ctx.lineTo(X, Y) : ctx.moveTo(X, Y);
  }
  ctx.stroke();

  // Start marker.
  // 起点标记。
  ctx.fillStyle = '#2fbf71';
  ctx.beginPath();
  ctx.arc(tx(pts[0][0]), ty(pts[0][1]), 6, 0, Math.PI * 2);
  ctx.fill();

  // End / cursor marker.
  // 终点 / 游标标记。
  ctx.fillStyle = '#e5534b';
  const last = Math.min(limit - 1, pts.length - 1);
  ctx.beginPath();
  ctx.arc(tx(pts[last][0]), ty(pts[last][1]), 6, 0, Math.PI * 2);
  ctx.fill();

  // Animated cursor dot.
  // 动画游标小点。
  if (cursorIdx !== undefined && cursorIdx < pts.length) {
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(tx(pts[cursorIdx][0]), ty(pts[cursorIdx][1]), 4, 0, Math.PI * 2);
    ctx.fill();
  }
}

// Play the gesture at up to 4 seconds, honoring intervals.
// 按 intervals 播放轨迹，最长压缩到 4 秒。
function playGesture() {
  if (!lastGesture) return;
  if (playTimer) { clearTimeout(playTimer); playTimer = null; }
  const g = lastGesture;
  const total = g.intervals.reduce((a, b) => a + b, 0) || 1;
  const speedup = total > 4 ? total / 4 : 1;
  let i = 0;
  $('#kplay-status').textContent = t('播放中…', 'playing…');
  const step = () => {
    drawKinematics(g, i);
    if (i >= g.points.length - 1) {
      $('#kplay-status').textContent = t('播放完成', 'done');
      playTimer = null;
      return;
    }
    const dt = Math.max(10, (g.intervals[i] * 1000) / speedup);
    i++;
    playTimer = setTimeout(step, dt);
  };
  step();
}

$('#kgo').addEventListener('click', generateGesture);
$('#kplay').addEventListener('click', playGesture);

// ========================================================== timing

// Draw a histogram on the given canvas.
// 在给定 canvas 上绘制直方图。
function drawHistogram(bins, canvas) {
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#0e1116';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  if (!bins.length) return;
  const pad = { l: 40, r: 12, t: 16, b: 30 };
  const iw = canvas.width - pad.l - pad.r;
  const ih = canvas.height - pad.t - pad.b;
  const maxCount = Math.max(...bins.map(b => b.count), 1);
  const bw = iw / bins.length;

  // X axis.
  // X 轴。
  ctx.strokeStyle = '#242c3a';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(pad.l, pad.t + ih);
  ctx.lineTo(pad.l + iw, pad.t + ih);
  ctx.stroke();

  // Bars.
  // 柱状。
  bins.forEach((b, i) => {
    const h = (b.count / maxCount) * ih;
    const x = pad.l + i * bw;
    ctx.fillStyle = '#4c8dff';
    ctx.fillRect(x, pad.t + ih - h, Math.max(1, bw - 1), h);
  });

  // Labels.
  // 标签。
  ctx.fillStyle = '#9aa7bd';
  ctx.font = '11px ui-monospace, monospace';
  ctx.fillText(bins[0].lo.toFixed(2), pad.l, canvas.height - 10);
  ctx.fillText(bins[bins.length - 1].hi.toFixed(2),
               pad.l + iw - 40, canvas.height - 10);
  ctx.fillText(String(maxCount), 6, pad.t + 10);
}

// Request a sample distribution and draw the histogram.
// 请求采样分布并绘制直方图。
async function sampleTiming() {
  try {
    const body = {
      n: Number($('#t_n').value),
      lo: Number($('#t_lo').value),
      hi: Number($('#t_hi').value),
      lognormal: $('#t_ln').checked,
      seed: seedOf($('#t_seed')),
      mu_ratio: Number($('#t_mu_ratio').value),
      sigma_range: [Number($('#t_sigma_lo').value), Number($('#t_sigma_hi').value)],
      delay_between_actions: [Number($('#t_db_lo').value), Number($('#t_db_hi').value)],
      delay_after_open: [Number($('#t_ao_lo').value), Number($('#t_ao_hi').value)],
      think_delay: [Number($('#t_th_lo').value), Number($('#t_th_hi').value)],
      start_jitter: [Number($('#t_sj_lo').value), Number($('#t_sj_hi').value)],
    };
    const data = await postJSON('/api/timing/sample', body);
    drawHistogram(data.bins, $('#cv-timing'));
    const s = data.stats;
    $('#tmeta').innerHTML =
      `n <b>${s.n}</b><br>` +
      `min <b>${s.min.toFixed(3)}</b><br>` +
      `max <b>${s.max.toFixed(3)}</b><br>` +
      `mean <b>${s.mean.toFixed(3)}</b><br>` +
      `median <b>${s.median.toFixed(3)}</b><br>` +
      `stdev <b>${s.stdev.toFixed(3)}</b>`;
  } catch (e) {
    $('#tmeta').textContent = t('错误', 'Error') + ': ' + e.message;
  }
}

$('#tgo').addEventListener('click', sampleTiming);

// ---------------------------------------------------------- wake window

// Draw the 24-hour wake window bar.
// 绘制 24 小时作息窗口条。
function drawWindow(info) {
  const cv = $('#cv-window');
  const ctx = cv.getContext('2d');
  ctx.clearRect(0, 0, cv.width, cv.height);
  ctx.fillStyle = '#0e1116';
  ctx.fillRect(0, 0, cv.width, cv.height);

  const pad = { l: 30, r: 30, t: 20, b: 30 };
  const iw = cv.width - pad.l - pad.r;
  const barH = 30;
  const y = pad.t;

  // Border.
  // 边框。
  ctx.strokeStyle = '#242c3a';
  ctx.strokeRect(pad.l, y, iw, barH);

  // In-window segments.
  // 窗口内区间。
  ctx.fillStyle = 'rgba(76,141,255,0.35)';
  for (const [s, e] of info.segments) {
    const x1 = pad.l + (s / 1440) * iw;
    const x2 = pad.l + (e / 1440) * iw;
    ctx.fillRect(x1, y, x2 - x1, barH);
  }

  // Hour ticks.
  // 小时刻度。
  ctx.fillStyle = '#9aa7bd';
  ctx.font = '11px ui-monospace, monospace';
  for (let h = 0; h <= 24; h += 6) {
    const x = pad.l + (h * 60 / 1440) * iw;
    ctx.fillRect(x - 1, y + barH, 2, 6);
    ctx.fillText(String(h).padStart(2, '0') + ':00', x - 14, y + barH + 20);
  }

  $('#wmeta').textContent =
    `start=${info.start} (${info.start_min}min) · end=${info.end} (${info.end_min}min) · ` +
    `${t('跨午夜', 'cross-midnight')} ${info.cross_midnight ? t('是', 'yes') : t('否', 'no')}`;
}

// Request wake-window segments and draw them.
// 请求作息窗口区间并绘制。
async function calcWindow() {
  try {
    const data = await postJSON('/api/timing/window', {
      wake_window: { start: $('#w_start').value, end: $('#w_end').value },
    });
    drawWindow(data);
  } catch (e) {
    $('#wmeta').textContent = t('错误', 'Error') + ': ' + e.message;
  }
}
$('#wgo').addEventListener('click', calcWindow);

// ---------------------------------------------------------- cooldown

// Simulate cooldowns and render the per-tap event list.
// 模拟冷却，渲染逐次点击事件列表。
async function simulateCooldown() {
  try {
    const body = {
      n: Number($('#c_n').value),
      cooldown_every: Number($('#c_every').value),
      cooldown_seconds: Number($('#c_seconds').value),
      cooldown_on_captcha: Number($('#c_on_captcha').value),
      seed: seedOf($('#c_seed')),
    };
    const data = await postJSON('/api/timing/cooldown', body);
    const rows = data.events.map(ev => {
      const cd = ev.cooldown != null ? ` <b style="color:#e5532b">CD ${ev.cooldown}s</b>` : '';
      return `<div class="ev">#${ev.tap}  delay=${ev.delay.toFixed(3)}s${cd}</div>`;
    }).join('');
    $('#cresult').innerHTML =
      `<p class="muted">${t('共', 'taps')}: ${data.n} · ${t('总耗时', 'total')} <b>${data.total.toFixed(2)}s</b> · ` +
      `${t('每 ' + data.cooldown_every + ' 次长停 ' + data.cooldown_seconds + 's',
          'long pause ' + data.cooldown_seconds + 's every ' + data.cooldown_every + ' taps')}</p>` +
      `<div class="evlist">${rows}</div>`;
  } catch (e) {
    $('#cresult').textContent = t('错误', 'Error') + ': ' + e.message;
  }
}
$('#cgo').addEventListener('click', simulateCooldown);

// ========================================================== sensors

let lastSensors = null;

// Collect sensor form values into a request body.
// 收集传感器表单字段为请求体。
function sBody() {
  return {
    mode: $('#s_mode').value,
    fs: Number($('#s_fs').value),
    duration: Number($('#s_duration').value),
    seed: seedOf($('#s_seed')),
    dead_std_threshold: Number($('#s_dead_std').value),
    gyro_dead_std: Number($('#s_gyro_dead').value),
    dead_zero_ratio_max: Number($('#s_dead_zero').value),
  };
}

// Request a sensor sequence and render it.
// 请求传感器序列并渲染。
async function generateSensors() {
  try {
    const data = await postJSON('/api/sensors/generate', sBody());
    lastSensors = data;
    drawSensors(data);
    const s = data.stats;
    const dead = data.is_dead
      ? '<span style="color:#e5534b"><b>' + t('是（死寂）', 'yes (dead)') + '</b></span>'
      : '<span style="color:#2fbf71"><b>' + t('否（活着）', 'no (alive)') + '</b></span>';
    $('#smeta').innerHTML =
      `${t('模式', 'mode')} <b>${data.mode}</b> · ${data.sample_count} ${t('采样点', 'samples')}<br>` +
      `${t('死寂判定', 'dead')}: ${dead}<br>` +
      `acc_x std=${s.acc_x_std.toFixed(4)} zero=${s.acc_x_zero.toFixed(2)}<br>` +
      `acc_y std=${s.acc_y_std.toFixed(4)} zero=${s.acc_y_zero.toFixed(2)}<br>` +
      `acc_z std=${s.acc_z_std.toFixed(4)} zero=${s.acc_z_zero.toFixed(2)}<br>` +
      `gyro_x std=${s.gyro_x_std.toFixed(4)} zero=${s.gyro_x_zero.toFixed(2)}<br>` +
      `gyro_y std=${s.gyro_y_std.toFixed(4)} zero=${s.gyro_y_zero.toFixed(2)}<br>` +
      `gyro_z std=${s.gyro_z_std.toFixed(4)} zero=${s.gyro_z_zero.toFixed(2)}`;
  } catch (e) {
    $('#smeta').textContent = t('错误', 'Error') + ': ' + e.message;
  }
}

// Draw two sub-charts: acc (top) and gyro (bottom).
// 绘制上下两个子图：加速度（上）与陀螺仪（下）。
function drawSensors(data) {
  const cv = $('#cv-sensors');
  const ctx = cv.getContext('2d');
  ctx.clearRect(0, 0, cv.width, cv.height);
  ctx.fillStyle = '#0e1116';
  ctx.fillRect(0, 0, cv.width, cv.height);

  const series = data.series;
  const n = series.t.length;
  if (!n) return;

  const halfH = (cv.height - 60) / 2;
  const pad = { l: 40, r: 20 };
  const iw = cv.width - pad.l - pad.r;

  // Draw one sub-chart with up to 3 axes.
  // 绘制一个最多三轴的子图。
  function drawAxis(keysArr, top, height, title) {
    ctx.fillStyle = '#9aa7bd';
    ctx.font = '12px ui-monospace, monospace';
    ctx.fillText(title, pad.l, top - 6);

    // Compute value range across keys.
    // 计算该组键的值域。
    let lo = Infinity, hi = -Infinity;
    for (const k of keysArr) for (const v of series[k]) {
      if (v < lo) lo = v; if (v > hi) hi = v;
    }
    if (!isFinite(lo) || !isFinite(hi) || hi === lo) { lo = -1; hi = 1; }

    // Border.
    // 边框。
    ctx.strokeStyle = '#242c3a';
    ctx.strokeRect(pad.l, top, iw, height);

    const tx = i => pad.l + (i / Math.max(1, n - 1)) * iw;
    const ty = v => top + height - ((v - lo) / (hi - lo)) * height;

    // Curves.
    // 曲线。
    for (const k of keysArr) {
      ctx.strokeStyle = COLORS[k];
      ctx.lineWidth = 1.4;
      ctx.beginPath();
      const arr = series[k];
      for (let i = 0; i < arr.length; i++) {
        const X = tx(i), Y = ty(arr[i]);
        i ? ctx.lineTo(X, Y) : ctx.moveTo(X, Y);
      }
      ctx.stroke();
    }

    // Legend.
    // 图例。
    ctx.font = '11px ui-monospace, monospace';
    let lx = pad.l + 6;
    for (const k of keysArr) {
      ctx.fillStyle = COLORS[k];
      ctx.fillRect(lx, top + 4, 10, 10);
      ctx.fillStyle = '#c3cddd';
      ctx.fillText(k, lx + 14, top + 13);
      lx += 90;
    }
  }

  drawAxis(['acc_x', 'acc_y', 'acc_z'], 20, halfH, '加速度 (m/s²)');
  drawAxis(['gyro_x', 'gyro_y', 'gyro_z'], 20 + halfH + 20, halfH, '陀螺仪 (rad/s)');
}

// Download the current sensor sequence as CSV.
// 把当前传感器序列下载为 CSV。
async function downloadCSV() {
  try {
    const res = await fetch('/api/sensors/csv', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sBody()),
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const blob = await res.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `sensors_${$('#s_mode').value}.csv`;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  } catch (e) {
    $('#smeta').textContent = t('错误', 'Error') + ': ' + e.message;
  }
}

$('#sgo').addEventListener('click', generateSensors);
$('#scsv').addEventListener('click', downloadCSV);

// ========================================================== first paint

// Trigger one render for every tab on first paint.
// 首屏触发每个 tab 的一次渲染。
applyLang();

// ========================================================== code generation
// ========================================================== 代码生成
//
// Generate a runnable Python snippet from the current form values.
// Pure frontend string building: no backend call, no new library features.
// 根据当前 tab 的表单值生成一段可直接运行的 Python 代码。
// 纯前端拼接当前选项，不调用后端，不新增库功能。

// Reasonable precision for numbers; empty seed -> None.
// 数字保留合理精度；空 seed 用 None。
function _fmt(v) {
  if (v === '' || v === null || v === undefined) return 'None';
  const n = Number(v);
  if (!isFinite(n)) return 'None';
  return Number.isInteger(n) ? String(n) : String(Number(n.toFixed(6)));
}

// Show the code block and its copy button.
// 显示代码块与复制按钮。
function _showCode(id, code) {
  const box = $('#' + id);
  const btn = $('#' + id.replace('-code', '-copy'));
  box.textContent = code;
  box.classList.remove('hidden');
  btn.classList.remove('hidden');
  btn.onclick = () => navigator.clipboard.writeText(code);
}

// Trajectory codegen: mirrors kBody().
// 轨迹代码生成：与 kBody() 对应。
function codeKinematics() {
  const body = kBody();
  const cfg = {
    enabled: body.enabled,
    steps_min: body.steps_min,
    steps_max: body.steps_max,
    px_per_step: body.px_per_step,
    duration_per_px: body.duration_per_px,
    duration_min: body.duration_min,
    duration_max: body.duration_max,
    perpendicular_ratio: body.perpendicular_ratio,
    jitter_sigma: body.jitter_sigma,
    jitter_tail_fraction: body.jitter_tail_fraction,
    overshoot_prob: body.overshoot_prob,
    overshoot_ratio: body.overshoot_ratio,
    use_ease_in_out: body.use_ease_in_out,
  };
  const code =
`from android_humanizer import Humanizer

# 同 seed 可复现整条轨迹 / same seed reproduces the same trajectory
h = Humanizer(seed=${_fmt(body.seed)})
g = h.gesture(
    (${_fmt(body.start[0])}, ${_fmt(body.start[1])}),
    (${_fmt(body.end[0])}, ${_fmt(body.end[1])}),
    for_slider=${body.for_slider ? 'True' : 'False'},
    exact_end=${body.exact_end ? 'True' : 'False'},
)
for (x, y), dt in zip(g.points, g.intervals):
    print(x, y, dt)

# 若要覆盖高级参数 / to override advanced params:
# h = Humanizer(
#     config={"kinematics": ${JSON.stringify(cfg)}},
#     seed=${_fmt(body.seed)},
# )
`;
  _showCode('k-code', code);
}

// Timing sample codegen. 延迟分布采样代码生成。
function codeTimingSample() {
  const n = Number($('#t_n').value);
  const lo = Number($('#t_lo').value);
  const hi = Number($('#t_hi').value);
  const ln = $('#t_ln').checked;
  const seed = seedOf($('#t_seed'));
  const tcfg = {
    mu_ratio: Number($('#t_mu_ratio').value),
    sigma_range: [Number($('#t_sigma_lo').value), Number($('#t_sigma_hi').value)],
  };
  const code =
`from android_humanizer import Humanizer

h = Humanizer(
    config={"timing": ${JSON.stringify(tcfg)}},
    seed=${_fmt(seed)},
)
samples = [h.timing.sample(${_fmt(lo)}, ${_fmt(hi)}, lognormal=${ln ? 'True' : 'False'})
           for _ in range(${_fmt(n)})]
print(min(samples), max(samples), sum(samples) / len(samples))
`;
  _showCode('t-code', code);
}

// Wake-window codegen. 作息窗口代码生成。
function codeTimingWindow() {
  const start = $('#w_start').value || '07:30';
  const end = $('#w_end').value || '23:00';
  const code =
`from android_humanizer import Humanizer

h = Humanizer(config={"timing": {"wake_window": {"start": "${start}", "end": "${end}"}}})
print("in window now:", h.in_wake_window())
`;
  _showCode('w-code', code);
}

// Cooldown codegen. 冷却模拟代码生成。
function codeTimingCooldown() {
  const n = Number($('#c_n').value);
  const every = Number($('#c_every').value);
  const seconds = Number($('#c_seconds').value);
  const seed = seedOf($('#c_seed'));
  const code =
`from android_humanizer import Humanizer

h = Humanizer(
    config={"timing": {"cooldown_every": ${_fmt(every)}, "cooldown_seconds": ${_fmt(seconds)}, "cooldown_on_captcha": ${_fmt(Number($('#c_on_captcha').value))}}},
    seed=${_fmt(seed)},
)
for i in range(1, ${_fmt(n)} + 1):
    d = h.timing.delay_between_actions()
    cd = h.timing.tap()
    print(i, d, cd)
`;
  _showCode('c-code', code);
}

// Sensors codegen (incl. CSV export). 传感器代码生成（含 CSV 导出）。
function codeSensors() {
  const body = sBody();
  const scfg = {
    dead_std_threshold: body.dead_std_threshold,
    gyro_dead_std: body.gyro_dead_std,
    dead_zero_ratio_max: body.dead_zero_ratio_max,
  };
  const code =
`from android_humanizer import Humanizer

h = Humanizer(
    config={"sensors": ${JSON.stringify(scfg)}},
    seed=${_fmt(body.seed)},
)
rows = h.sensors.generate(mode=${JSON.stringify(body.mode)}, fs=${_fmt(body.fs)}, duration=${_fmt(body.duration)})
print("samples:", len(rows))
print("dead:", h.sensors.is_dead(rows))

# 导出 CSV / export CSV
import csv
with open("sensors_${body.mode}.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["t", "acc_x", "acc_y", "acc_z", "lin_x", "lin_y", "lin_z",
                "gyro_x", "gyro_y", "gyro_z", "mag_x", "mag_y", "mag_z"])
    for r in rows:
        w.writerow([r["t"], *r["acc"], *r["lin"], *r["gyro"], *r["mag"]])
`;
  _showCode('s-code', code);
}

// Bind buttons. 绑定按钮。
$('#k-codegen').addEventListener('click', codeKinematics);
$('#t-codegen').addEventListener('click', codeTimingSample);
$('#w-codegen').addEventListener('click', codeTimingWindow);
$('#c-codegen').addEventListener('click', codeTimingCooldown);
$('#s-codegen').addEventListener('click', codeSensors);
