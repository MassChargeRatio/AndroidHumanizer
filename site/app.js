'use strict';

/* ------------------------------------------------------------------
 * touch-humanization · browser demo
 * Same algorithms as the Python kinematics module:
 *   cubic bezier + Fitts steps + smoothstep profile + tail Gaussian
 *   tremor + overshoot pull-back
 * Random source: mulberry32 (instance-level PRNG, seed-reproducible).
 * Note: the JS PRNG differs from Python's, so the same seed does NOT
 *   give bit-identical output; statistical characteristics
 *   (mean / quantiles / shape) do match.
 *
 * touch-humanization · 浏览器演示
 * 与 Python 版 kinematics 同一套算法：
 *   三次贝塞尔 + Fitts 步数 + smoothstep 速度轮廓 + 末段高斯微颤 + 过冲回拉
 * 随机源：mulberry32（实例级 PRNG，seed 可复现）。
 * 注：JS 与 Python 的 PRNG 实现不同，故同 seed 不是逐位一致，
 *     但统计特征（均值/分位/形态）一致。
 * ------------------------------------------------------------------ */

// Tunable defaults, mirroring config.py DEFAULTS.kinematics.
// 可调默认值，与 config.py 的 DEFAULTS.kinematics 对齐。
const DEFAULTS = {
  stepsMin: 20,
  stepsMax: 60,
  pxPerStep: 15,
  durationPerPx: 0.0007,
  durationMin: 0.3,
  durationMax: 1.5,
  perpendicularRatio: 0.12,
  jitterSigma: 1.2,
  jitterTailFraction: 0.25,
  overshootProb: 0.25,
  overshootRatio: 0.06,
};

const $ = s => document.querySelector(s);
// Clamp helper. 区间钳制辅助函数。
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

// mulberry32: tiny 32-bit seeded PRNG.
// mulberry32：微型 32 位带种子 PRNG。
function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Box-Muller Gaussian sample (no numpy equivalent needed in JS).
// Box-Muller 高斯采样。
function gauss(rnd, mu = 0, sigma = 1) {
  let u1 = rnd();
  if (u1 < 1e-12) u1 = 1e-12;
  const u2 = rnd();
  return mu + sigma * Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
}

// Slow-fast-slow profile: 3t^2 - 2t^3.
// 慢-快-慢速度轮廓：3t^2 - 2t^3。
const smoothstep = t => {
  t = clamp(t, 0, 1);
  return t * t * (3 - 2 * t);
};

// Sample a point on a cubic bezier curve.
// 三次贝塞尔曲线采样。
function bezier3(p0, p1, p2, p3, t) {
  const u = 1 - t;
  const x = u * u * u * p0[0] + 3 * u * u * t * p1[0] +
            3 * u * t * t * p2[0] + t * t * t * p3[0];
  const y = u * u * u * p0[1] + 3 * u * u * t * p1[1] +
            3 * u * t * t * p2[1] + t * t * t * p3[1];
  return [x, y];
}

// Control points: one-sided offset perpendicular to the main direction.
// 控制点：沿垂直于主方向的单侧随机偏移。
function controlPoints(rnd, start, end, dist, ratio) {
  const dx = end[0] - start[0];
  const dy = end[1] - start[1];
  if (dist < 1e-6) return [start, end];
  // Unit normal vector. 单位法向量。
  const nx = -dy / dist, ny = dx / dist;
  // Random side (left or right). 随机取正/负侧。
  const side = rnd() < 0.5 ? 1 : -1;
  const amp = dist * ratio * (0.5 + rnd() * 0.9);
  const mx = (start[0] + end[0]) / 2;
  const my = (start[1] + end[1]) / 2;
  return [
    [mx + nx * side * amp, my + ny * side * amp],
    [mx + nx * side * amp * (0.5 + rnd() * 0.7),
     my + ny * side * amp * (0.5 + rnd() * 0.7)],
  ];
}

// Generate one human-like trajectory (main entry).
// 生成一条拟人轨迹（主入口）。
function generate(start, end, opts) {
  const o = Object.assign({}, DEFAULTS, opts || {});
  const rnd = mulberry32(o.seed >>> 0);
  const p0 = [start[0], start[1]];
  const p3 = [end[0], end[1]];
  const dx = p3[0] - p0[0], dy = p3[1] - p0[1];
  const dist = Math.hypot(dx, dy);

  // Degenerate distance: just two points. 距离过短：只返回两个点。
  if (dist < 1.0) {
    return { points: [p0, p3], intervals: [0.02], duration: 0.02,
             distance: dist, steps: 2, slider: !!o.forSlider, seed: o.seed };
  }

  // Fitts-style step count and duration. Fitts 风格步数与总时长。
  const steps = Math.round(clamp(dist / o.pxPerStep, o.stepsMin, o.stepsMax));
  const duration = clamp(dist * o.durationPerPx, o.durationMin, o.durationMax);

  // Slider drag branch: near-horizontal, head/tail pinned.
  // 滑块拖拽分支：近乎纯水平、头尾贴轨道。
  if (o.forSlider) {
    const ts = [];
    for (let i = 0; i < steps; i++) ts.push(smoothstep(i / (steps - 1)));
    const pts = [];
    for (let i = 0; i < steps; i++) {
      const x = p0[0] + dx * ts[i];
      // Tiny vertical jitter only in the middle; head/tail stay on track.
      // 仅中段有极小 y 抖动；头尾保持贴轨道。
      const y = (i >= 2 && i <= steps - 3) ? p0[1] + gauss(rnd, 0, 0.5)
                                           : p0[1];
      pts.push([x, y]);
    }
    const ivs = [];
    for (let i = 1; i < steps; i++) {
      ivs.push(duration * (ts[i] - ts[i - 1]) * (0.7 + rnd() * 0.6));
    }
    if (o.exactEnd !== false) pts[pts.length - 1] = p3;
    return { points: pts.map(roundPt), intervals: ivs,
             duration: ivs.reduce((a, b) => a + b, 0),
             distance: dist, steps: pts.length, slider: true, seed: o.seed };
  }

  // Overshoot: pass the target then pull back. 过冲：先越过终点再回拉。
  let overshoot = 0;
  if (rnd() < o.overshootProb) overshoot = dist * o.overshootRatio * (0.6 + rnd() * 0.6);
  const s = overshoot > 0 ? overshoot / dist : 0;
  const p3o = [p0[0] + dx * (1 + s), p0[1] + dy * (1 + s)];

  const [p1, p2] = controlPoints(rnd, p0, p3o, dist + overshoot, o.perpendicularRatio);
  const pts = [];
  for (let i = 0; i < steps; i++) pts.push(bezier3(p0, p1, p2, p3o, i / (steps - 1)));

  // Append pull-back points after overshoot. 过冲后追加回拉点。
  if (overshoot > 0) {
    const backN = Math.max(3, Math.floor(steps / 6));
    for (let i = 1; i <= backN; i++) {
      const f = 1 - i / backN;
      pts.push([p3[0] + (p3o[0] - p3[0]) * f, p3[1] + (p3o[1] - p3[1]) * f]);
    }
  }

  // Speed profile + per-step jitter. 速度轮廓 + 每步随机扰动。
  const n = pts.length;
  const ts = [];
  for (let i = 0; i < n; i++) ts.push(smoothstep(i / (n - 1)));
  const ivs = [];
  for (let i = 1; i < n; i++) ivs.push(duration * (ts[i] - ts[i - 1]) * (0.6 + rnd() * 0.8));

  // Tail jitter: human finger tremor at the end of the move.
  // 末段微颤：动作结尾的手指生理抖动。
  if (o.jitterSigma > 0) {
    const tailFrom = Math.floor(n * (1 - o.jitterTailFraction));
    for (let i = tailFrom; i < n - 1; i++) {
      const f = (i - tailFrom) / Math.max(1, n - 1 - tailFrom);
      const sigma = o.jitterSigma * (0.3 + 0.7 * f);
      pts[i] = [pts[i][0] + gauss(rnd, 0, sigma), pts[i][1] + gauss(rnd, 0, sigma)];
    }
  }

  // Force exact end + small "settle" delay. 强制终点精确 + 末段落定延迟。
  if (o.exactEnd !== false) {
    pts[pts.length - 1] = p3;
    ivs[ivs.length - 1] += 0.05 + rnd() * 0.15;
  }

  return { points: pts.map(roundPt), intervals: ivs,
           duration: ivs.reduce((a, b) => a + b, 0),
           distance: dist, steps: pts.length, slider: false, seed: o.seed };
}

// Round a point to integer coords. 坐标取整。
const roundPt = p => [Math.round(p[0]), Math.round(p[1])];

/* ---------------- drawing / 绘图 ---------------- */
function draw(g) {
  const cv = $('#cv');
  const ctx = cv.getContext('2d');
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, cv.width, cv.height);
  ctx.fillStyle = '#0e1116';
  ctx.fillRect(0, 0, cv.width, cv.height);

  const pts = g.points;
  const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
  const minX = Math.min(...xs) - 30, maxX = Math.max(...xs) + 30;
  const minY = Math.min(...ys) - 30, maxY = Math.max(...ys) + 30;
  const w = maxX - minX || 1, h = maxY - minY || 1;
  const scale = Math.min((cv.width - 60) / w, (cv.height - 60) / h);
  const ox = 30 + (cv.width - 60 - w * scale) / 2;
  const oy = 30 + (cv.height - 60 - h * scale) / 2;
  const tx = x => ox + (x - minX) * scale;
  const ty = y => oy + (y - minY) * scale;

  // Grid. 网格。
  ctx.strokeStyle = 'rgba(255,255,255,0.06)';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 10; i++) {
    const gx = ox + (cv.width - 60) * i / 10;
    const gy = oy + (cv.height - 60) * i / 10;
    ctx.beginPath(); ctx.moveTo(gx, oy); ctx.lineTo(gx, oy + h * scale); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(ox, gy); ctx.lineTo(ox + w * scale, gy); ctx.stroke();
  }

  // Trajectory. 轨迹。
  ctx.strokeStyle = '#4c8dff';
  ctx.lineWidth = 2;
  ctx.lineJoin = 'round';
  ctx.beginPath();
  pts.forEach((p, i) => {
    const X = tx(p[0]), Y = ty(p[1]);
    i ? ctx.lineTo(X, Y) : ctx.moveTo(X, Y);
  });
  ctx.stroke();

  // Sample points. 采样点。
  ctx.fillStyle = 'rgba(76,141,255,0.45)';
  pts.forEach(p => {
    ctx.beginPath();
    ctx.arc(tx(p[0]), ty(p[1]), 1.6, 0, Math.PI * 2);
    ctx.fill();
  });

  // Start / end markers. 起终点标记。
  ctx.fillStyle = '#2fbf71';
  ctx.beginPath(); ctx.arc(tx(pts[0][0]), ty(pts[0][1]), 7, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#e5534b';
  ctx.beginPath();
  ctx.arc(tx(pts[pts.length - 1][0]), ty(pts[pts.length - 1][1]), 7, 0, Math.PI * 2);
  ctx.fill();
}

/* ---------------- interaction / 交互 ---------------- */
function readNum(id, dflt) {
  const v = $(id).value;
  return v === '' ? dflt : Number(v);
}

// Regenerate and redraw; also show step-interval stats.
// 重新生成并重绘；同时展示步间隔统计。
function render() {
  const start = [readNum('#sx', 100), readNum('#sy', 1800)];
  const end = [readNum('#ex', 900), readNum('#ey', 400)];
  const seed = (readNum('#seed', Math.floor(Math.random() * 1e9)) >>> 0);
  $('#seed').value = seed;

  const opts = {
    seed,
    forSlider: $('#slider').checked,
    stepsMin: readNum('#stepsMin', DEFAULTS.stepsMin),
    stepsMax: readNum('#stepsMax', DEFAULTS.stepsMax),
    pxPerStep: readNum('#pxPerStep', DEFAULTS.pxPerStep),
    perpendicularRatio: readNum('#perpH', DEFAULTS.perpendicularRatio),
    jitterSigma: readNum('#jitter', DEFAULTS.jitterSigma),
    overshootProb: readNum('#overshoot', DEFAULTS.overshootProb),
  };
  const t0 = performance.now();
  const g = generate(start, end, opts);
  const ms = performance.now() - t0;

  draw(g);

  const ivs = g.intervals.slice().sort((a, b) => a - b);
  const p = q => ivs[Math.min(ivs.length - 1, Math.round(q * (ivs.length - 1)))] || 0;
  $('#meta').innerHTML =
    `<span>点数 / points <b>${g.steps}</b></span>` +
    `<span>直线距离 / distance <b>${g.distance.toFixed(1)}px</b></span>` +
    `<span>总时长 / duration <b>${g.duration.toFixed(3)}s</b></span>` +
    `<span>步间隔 / step gap p50 <b>${(p(0.5) * 1000).toFixed(0)}ms</b></span>` +
    `<span>p95 <b>${(p(0.95) * 1000).toFixed(0)}ms</b></span>` +
    `<span>模式 / mode <b>${g.slider ? '滑块 / slider' : '滑动 / swipe'}</b></span>` +
    `<span class="ok">生成 / gen ${ms.toFixed(1)}ms</span>`;
}

$('#go').addEventListener('click', render);
$('#rand').addEventListener('click', () => {
  $('#seed').value = Math.floor(Math.random() * 1e9);
  render();
});
$('#slider').addEventListener('change', render);
['#sx', '#sy', '#ex', '#ey'].forEach(id =>
  $(id).addEventListener('change', render));

render();

// ========================================================== code generation
// ========================================================== 代码生成
//
// Build a runnable Python snippet from the current demo form values.
// Pure frontend string building; no backend call.
// 根据当前演示表单值拼接可直接运行的 Python 代码；纯前端，无后端调用。

function fmtV(v) {
  if (v === '' || v === null || v === undefined) return 'None';
  const n = Number(v);
  if (!isFinite(n)) return 'None';
  return Number.isInteger(n) ? String(n) : String(Number(n.toFixed(6)));
}

function showCode(code) {
  const box = $('#code-out');
  const btn = $('#code-copy');
  box.textContent = code;
  box.classList.remove('hidden');
  btn.classList.remove('hidden');
  btn.onclick = () => navigator.clipboard.writeText(code);
}

// Trajectory codegen adapted to this page's form ids.
// 轨迹代码生成：适配本页的表单 id。
function codeTrajectory() {
  const sx = readNum('#sx', 100), sy = readNum('#sy', 1800);
  const ex = readNum('#ex', 900), ey = readNum('#ey', 400);
  const seed = $('#seed').value.trim() === '' ? 'None' : $('#seed').value.trim();
  const forSlider = $('#slider').checked;
  const cfg = {
    steps_min: readNum('#stepsMin', 20),
    steps_max: readNum('#stepsMax', 60),
    px_per_step: readNum('#pxPerStep', 15),
    perpendicular_ratio: readNum('#perpH', 0.12),
    jitter_sigma: readNum('#jitter', 1.2),
    overshoot_prob: readNum('#overshoot', 0.25),
  };
  const code =
`from touch_humanization import Humanizer

# 同 seed 可复现整条轨迹（JS 演示与 Python 的 PRNG 实现不同，
# 统计特征一致但同 seed 不逐位一致）/ same seed reproduces in Python;
# note the JS demo PRNG differs from Python's, statistics match.
h = Humanizer(seed=${seed})
g = h.gesture(
    (${fmtV(sx)}, ${fmtV(sy)}),
    (${fmtV(ex)}, ${fmtV(ey)}),
    for_slider=${forSlider ? 'True' : 'False'},
    exact_end=True,
)
for (x, y), dt in zip(g.points, g.intervals):
    print(x, y, dt)

# 若要覆盖高级参数 / to override advanced params:
# h = Humanizer(
#     config={"kinematics": ${JSON.stringify(cfg)}},
#     seed=${seed},
# )
`;
  showCode(code);
}

$('#code-btn').addEventListener('click', codeTrajectory);
