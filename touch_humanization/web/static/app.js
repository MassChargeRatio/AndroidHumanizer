'use strict';

const $ = s => document.querySelector(s);

async function generate() {
  const body = {
    start: [Number($('#sx').value), Number($('#sy').value)],
    end: [Number($('#ex').value), Number($('#ey').value)],
    seed: $('#seed').value === '' ? null : Number($('#seed').value),
    for_slider: $('#slider').checked,
  };
  const res = await fetch('/api/gesture', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!data.ok) {
    $('#meta').textContent = '错误：' + data.error;
    return;
  }
  draw(data.gesture);
}

function draw(g) {
  const cv = $('#cv');
  const ctx = cv.getContext('2d');
  ctx.clearRect(0, 0, cv.width, cv.height);
  ctx.fillStyle = '#0e1116';
  ctx.fillRect(0, 0, cv.width, cv.height);

  const pts = g.points;
  if (!pts.length) return;
  const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
  const minX = Math.min(...xs) - 20, maxX = Math.max(...xs) + 20;
  const minY = Math.min(...ys) - 20, maxY = Math.max(...ys) + 20;
  const w = maxX - minX || 1, h = maxY - minY || 1;
  const scale = Math.min((cv.width - 40) / w, (cv.height - 40) / h);
  const ox = 20 + (cv.width - 40 - w * scale) / 2;
  const oy = 20 + (cv.height - 40 - h * scale) / 2;
  const tx = x => ox + (x - minX) * scale;
  const ty = y => oy + (y - minY) * scale;

  ctx.strokeStyle = '#4c8dff';
  ctx.lineWidth = 2;
  ctx.beginPath();
  pts.forEach((p, i) => {
    const X = tx(p[0]), Y = ty(p[1]);
    i ? ctx.lineTo(X, Y) : ctx.moveTo(X, Y);
  });
  ctx.stroke();

  ctx.fillStyle = '#2fbf71';
  ctx.beginPath();
  ctx.arc(tx(pts[0][0]), ty(pts[0][1]), 6, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = '#e5534b';
  ctx.beginPath();
  ctx.arc(tx(pts[pts.length - 1][0]), ty(pts[pts.length - 1][1]), 6, 0, Math.PI * 2);
  ctx.fill();

  $('#meta').textContent =
    `点数 ${g.steps} · 距离 ${g.distance.toFixed(1)}px · 时长 ${g.duration.toFixed(3)}s`
    + (g.for_slider ? ' · 滑块模式' : '');
}

$('#go').addEventListener('click', generate);
generate();
