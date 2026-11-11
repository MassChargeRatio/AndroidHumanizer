# -*- coding: utf-8 -*-
"""Local interactive Web UI: kinematics / timing / sensors, all covered.

Only listens on 127.0.0.1; zero third-party dependencies (stdlib http.server).

API:
  GET  /api/health
  POST /api/gesture          Generate a human gesture trajectory
  POST /api/timing/sample    Sample delay distribution + histogram
  POST /api/timing/window    Wake-window segments
  POST /api/timing/cooldown  Cooldown simulation (long pause every N taps)
  POST /api/sensors/generate Sensor sequence + stats + deadness
  POST /api/sensors/csv      Export CSV (text/csv)

本地交互式 Web UI：轨迹 / 时序 / 传感器 三模块全覆盖。

只监听 127.0.0.1；零第三方依赖（stdlib http.server）。

API：
  GET  /api/health
  POST /api/gesture          生成人类化手势轨迹
  POST /api/timing/sample    采样延迟分布 + 直方图
  POST /api/timing/window    作息窗口区间
  POST /api/timing/cooldown  冷却模拟（每 N 次点击长停）
  POST /api/sensors/generate 传感器序列 + 统计 + 死寂判定
  POST /api/sensors/csv      导出 CSV（text/csv）
"""
from __future__ import annotations

import argparse
import csv
import io
import ipaddress
import json
import math
import os
import posixpath
import statistics
import sys
import urllib.parse
import webbrowser
from collections.abc import Iterable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ..humanize import Humanizer

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

# Bound request and sensor sizes so the unauthenticated local server cannot be
# exhausted by accidental or hostile oversized requests.
# 限制请求体与传感器样本规模，避免本地无认证服务被异常请求耗尽资源。
MAX_REQUEST_BODY = 256 * 1024
MAX_SENSOR_FS = 500.0
MAX_SENSOR_DURATION = 60.0
MAX_SENSOR_SAMPLES = 30_000


class _ClientError(Exception):
    """An expected request error with an HTTP status code."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message

# ---------------------------------------------------------------- helpers
# ---------------------------------------------------------------- 工具函数


def _json_bytes(obj) -> bytes:
    # UTF-8 JSON encoding.
    # UTF-8 JSON 编码。
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")


def _parse_xy(v, default):
    # Accept an exact [x, y] pair or {x, y}; omitted values use the default.
    # 只接受恰好两个坐标的 [x, y] 或 {x, y}；未提供时才使用默认值。
    if v is None:
        return default
    if isinstance(v, (list, tuple)) and len(v) == 2:
        values = v
    elif isinstance(v, dict) and set(v) == {"x", "y"}:
        values = (v["x"], v["y"])
    else:
        raise ValueError("坐标必须是 [x, y] 或仅含 x、y 的对象")
    try:
        x, y = float(values[0]), float(values[1])
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("坐标必须是有限数值") from exc
    if not math.isfinite(x) or not math.isfinite(y):
        raise ValueError("坐标必须是有限数值")
    return x, y


def _parse_hhmm(value: str) -> int:
    # Strictly parse a 24-hour HH:MM value.
    # 严格解析 24 小时制 HH:MM。
    try:
        parts = str(value).split(":")
        if len(parts) != 2:
            raise ValueError
        hour, minute = (int(part) for part in parts)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"无效时间 {value!r}；格式应为 HH:MM") from exc
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"无效时间 {value!r}；小时须为 00-23，分钟须为 00-59")
    return hour * 60 + minute


def _sensor_request(body: dict):
    # Validate sensor request size before allocating generated rows.
    # 在创建样本前校验采样率、时长与总点数。
    mode = str(body.get("mode", "resting"))
    try:
        fs = float(body.get("fs", 100.0))
        duration = float(body.get("duration", 5.0))
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("fs 和 duration 必须是有效数值") from exc
    if not math.isfinite(fs) or not math.isfinite(duration):
        raise ValueError("fs 和 duration 必须是有限数值")
    if not (0 < fs <= MAX_SENSOR_FS):
        raise ValueError(f"fs 必须大于 0 且不超过 {MAX_SENSOR_FS:g}")
    if not (0 < duration <= MAX_SENSOR_DURATION):
        raise ValueError(f"duration 必须大于 0 且不超过 {MAX_SENSOR_DURATION:g}")
    sample_count = max(2, int(fs * duration))
    if sample_count > MAX_SENSOR_SAMPLES:
        raise ValueError(
            f"样本数不能超过 {MAX_SENSOR_SAMPLES}，请降低 fs 或 duration"
        )
    seed = body.get("seed")
    try:
        seed = int(seed) if seed not in (None, "") else None
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("seed 必须是整数") from exc
    return mode, fs, duration, seed


def _pick(body: dict, keys: Iterable[str]) -> dict:
    # Pick only the known keys from a request body.
    # 只取请求体里已知的键。
    out = {}
    for k in keys:
        if k in body and body[k] is not None:
            out[k] = body[k]
    return out


# Whitelisted config keys per sub-module.
# 每个子模块的白名单配置键。
KINEMATICS_KEYS = [
    "enabled", "steps_min", "steps_max", "px_per_step",
    "duration_per_px", "duration_min", "duration_max",
    "perpendicular_ratio", "use_ease_in_out",
    "jitter_sigma", "jitter_tail_fraction",
    "overshoot_prob", "overshoot_ratio",
]

TIMING_KEYS = [
    "mu_ratio", "sigma_range",
    "delay_between_actions", "delay_after_open", "think_delay", "start_jitter",
    "wake_window", "cooldown_every", "cooldown_seconds", "cooldown_on_captcha",
]

SENSORS_KEYS = [
    "fs", "duration", "mode",
    "dead_std_threshold", "gyro_dead_std", "dead_zero_ratio_max",
]


def _kinematics_cfg(body: dict) -> dict:
    return _pick(body, KINEMATICS_KEYS)


def _timing_cfg(body: dict) -> dict:
    return _pick(body, TIMING_KEYS)


def _sensors_cfg(body: dict) -> dict:
    return _pick(body, SENSORS_KEYS)


def _histogram(values: list, bins: int = 30) -> list:
    # Build a simple histogram of the samples.
    # 构造采样值的简单直方图。
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi <= lo:
        return [{"lo": lo, "hi": hi, "count": len(values)}]
    step = (hi - lo) / bins
    out = [{"lo": lo + i * step, "hi": lo + (i + 1) * step, "count": 0}
           for i in range(bins)]
    for v in values:
        idx = min(bins - 1, max(0, int((v - lo) / step)))
        out[idx]["count"] += 1
    return out


def _downsample(values: list, max_points: int = 600) -> list:
    # Reduce series length for frontend rendering.
    # 缩减序列长度以便前端渲染。
    n = len(values)
    if n <= max_points:
        return list(values)
    stride = n / max_points
    out = []
    for i in range(max_points):
        out.append(values[min(n - 1, int(i * stride))])
    return out


def _window_segments(start_min: int, end_min: int) -> list:
    """Return in-window minute segments within [0, 1440].

    返回 [0,1440] 内「在窗口内」的分钟区间列表。
    """
    if start_min <= end_min:
        return [[start_min, end_min]]
    # Cross midnight: [start, 1440] + [0, end].
    # 跨午夜：[start, 1440] + [0, end]。
    return [[start_min, 1440], [0, end_min]]


# ---------------------------------------------------------------- Handler


class Handler(BaseHTTPRequestHandler):
    server_version = "touch-humanization-web"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        # Silence default access log.
        # 静音默认访问日志。
        pass

    # ---------- response helpers ----------
    # ---------- 基础响应 ----------

    def _send(self, code: int, body: bytes, ctype: str,
              extra_headers: dict | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
        )
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionAbortedError):
            pass

    def _json(self, obj, code: int = 200) -> None:
        self._send(code, _json_bytes(obj), "application/json; charset=utf-8")

    def _error(self, code: int, msg: str) -> None:
        self._json({"ok": False, "error": msg}, code)

    def _valid_host(self) -> bool:
        # Defend the loopback service against cross-origin DNS-rebinding requests.
        # 校验 Host，降低 DNS rebinding 将外部网页导向本地服务的风险。
        raw = self.headers.get("Host", "")
        try:
            parsed = urllib.parse.urlsplit("//" + raw)
            hostname = (parsed.hostname or "").lower()
            port = parsed.port
        except ValueError:
            return False
        expected_port = self.server.server_address[1]
        return hostname in ("127.0.0.1", "localhost") and port in (None, expected_port)

    def _read_body(self) -> dict:
        # Read a bounded JSON object body.
        # 读取有大小上限的 JSON 对象请求体。
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            return {}
        try:
            n = int(raw_length)
        except (TypeError, ValueError) as exc:
            raise _ClientError(400, "无效的 Content-Length") from exc
        if n < 0:
            raise _ClientError(400, "无效的 Content-Length")
        if n == 0:
            return {}
        if n > MAX_REQUEST_BODY:
            raise _ClientError(413, f"请求体不能超过 {MAX_REQUEST_BODY} 字节")
        if self.headers.get_content_type() != "application/json":
            raise _ClientError(415, "Content-Type 必须为 application/json")
        raw = self.rfile.read(n)
        if len(raw) != n:
            raise _ClientError(400, "请求体长度与 Content-Length 不匹配")
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _ClientError(400, "请求体必须是有效的 UTF-8 JSON") from exc
        if not isinstance(body, dict):
            raise _ClientError(400, "JSON 请求体必须是对象")
        return body

    # ---------- GET ----------

    def do_GET(self):
        if not self._valid_host():
            return self._error(403, "forbidden host")
        u = urllib.parse.urlparse(self.path)
        path = u.path
        if path in ("/", "/index.html"):
            return self._serve_page("index.html")
        if path.startswith("/static/"):
            return self._serve_static(path[len("/static/"):])
        if path == "/api/health":
            return self._json({"ok": True})
        return self._error(404, f"not found: {path}")

    def _serve_page(self, name: str) -> None:
        # Serve a top-level HTML page from static/.
        # 从 static/ 目录提供顶层 HTML 页面。
        p = os.path.join(STATIC_DIR, name)
        try:
            with open(p, "rb") as f:
                data = f.read()
        except OSError as e:
            return self._send(500, str(e).encode("utf-8"),
                              "text/plain; charset=utf-8")
        self._send(200, data, "text/html; charset=utf-8")

    def _serve_static(self, rel: str) -> None:
        # Path-traversal protected static file serving.
        # 防路径穿越的静态文件服务。
        rel = posixpath.normpath(urllib.parse.unquote(rel))
        if rel.startswith("..") or os.path.isabs(rel):
            return self._send(403, b"forbidden", "text/plain; charset=utf-8")
        full = os.path.realpath(os.path.join(STATIC_DIR, rel))
        if not full.startswith(os.path.realpath(STATIC_DIR) + os.sep):
            return self._send(403, b"forbidden", "text/plain; charset=utf-8")
        if not os.path.isfile(full):
            return self._send(404, b"not found", "text/plain; charset=utf-8")
        ext = os.path.splitext(full)[1].lower()
        ctype = {".html": "text/html; charset=utf-8",
                 ".js": "application/javascript; charset=utf-8",
                 ".css": "text/css; charset=utf-8"}.get(ext, "application/octet-stream")
        with open(full, "rb") as f:
            self._send(200, f.read(), ctype)

    # ---------- POST dispatch ----------
    # ---------- POST 分发 ----------

    def do_POST(self):
        if not self._valid_host():
            return self._error(403, "forbidden host")
        u = urllib.parse.urlparse(self.path)
        routes = {
            "/api/gesture": self._api_gesture,
            "/api/timing/sample": self._api_timing_sample,
            "/api/timing/window": self._api_timing_window,
            "/api/timing/cooldown": self._api_timing_cooldown,
            "/api/sensors/generate": self._api_sensors_generate,
            "/api/sensors/csv": self._api_sensors_csv,
        }
        fn = routes.get(u.path)
        if fn is None:
            return self._error(404, f"not found: {u.path}")
        try:
            body = self._read_body()
        except _ClientError as exc:
            return self._error(exc.status, exc.message)
        try:
            fn(body)
        except (ValueError, TypeError, OverflowError) as exc:
            self._error(400, str(exc) or "invalid request")
        except Exception:
            # Do not expose stack details or local paths to HTTP clients.
            # 不向 HTTP 客户端暴露堆栈信息或本机路径。
            self._error(500, "internal server error")

    # ---------- /api/gesture ----------

    def _api_gesture(self, body: dict) -> None:
        start = _parse_xy(body.get("start"), (100, 1800))
        end = _parse_xy(body.get("end"), (900, 400))
        seed = body.get("seed")
        seed = int(seed) if seed not in (None, "") else None
        for_slider = bool(body.get("for_slider", False))
        exact_end = bool(body.get("exact_end", True))
        kcfg = _kinematics_cfg(body)
        cfg = {"kinematics": kcfg} if kcfg else None
        h = Humanizer(config=cfg, seed=seed)
        g = h.gesture(start, end, for_slider=for_slider, exact_end=exact_end)
        self._json({"ok": True, "gesture": g.as_dict()})

    # ---------- /api/timing/sample ----------

    def _api_timing_sample(self, body: dict) -> None:
        n = max(1, min(20000, int(body.get("n", 2000))))
        lo = float(body.get("lo", 0.6))
        hi = float(body.get("hi", 2.2))
        lognormal = bool(body.get("lognormal", True))
        seed = body.get("seed")
        seed = int(seed) if seed not in (None, "") else None
        tcfg = _timing_cfg(body)
        cfg = {"timing": tcfg} if tcfg else None
        h = Humanizer(config=cfg, seed=seed)
        samples = [h.timing.sample(lo, hi, lognormal=lognormal) for _ in range(n)]
        stats = {
            "n": n,
            "min": min(samples),
            "max": max(samples),
            "mean": statistics.fmean(samples),
            "median": statistics.median(samples),
            "stdev": statistics.pstdev(samples),
        }
        self._json({
            "ok": True,
            "samples": samples,
            "bins": _histogram(samples, bins=40),
            "stats": stats,
        })

    # ---------- /api/timing/window ----------

    def _api_timing_window(self, body: dict) -> None:
        ww = body.get("wake_window") or {}
        if not isinstance(ww, dict):
            raise ValueError("wake_window 必须是对象")
        start = str(ww.get("start", "07:30"))
        end = str(ww.get("end", "23:00"))
        s_min, e_min = _parse_hhmm(start), _parse_hhmm(end)
        segs = _window_segments(s_min, e_min)
        self._json({
            "ok": True,
            "start": start,
            "end": end,
            "start_min": s_min,
            "end_min": e_min,
            "segments": segs,
            "cross_midnight": s_min > e_min,
        })

    # ---------- /api/timing/cooldown ----------

    def _api_timing_cooldown(self, body: dict) -> None:
        n = max(1, min(500, int(body.get("n", 50))))
        cfg_over = _timing_cfg(body)
        seed = body.get("seed")
        seed = int(seed) if seed not in (None, "") else None
        h = Humanizer(config={"timing": cfg_over} if cfg_over else None, seed=seed)
        events = []
        total = 0.0
        for i in range(1, n + 1):
            delay = h.timing.delay_between_actions()
            cd = h.timing.tap()
            events.append({
                "tap": i,
                "delay": round(delay, 4),
                "cooldown": round(cd, 4) if cd else None,
            })
            total += delay + (cd or 0)
        self._json({
            "ok": True,
            "n": n,
            "events": events,
            "total": round(total, 4),
            "cooldown_every": h.timing.cooldown_every,
            "cooldown_seconds": h.timing.cooldown_seconds,
        })

    # ---------- /api/sensors/generate ----------

    def _api_sensors_generate(self, body: dict) -> None:
        mode, fs, duration, seed = _sensor_request(body)
        cfg_over = _sensors_cfg(body)
        h = Humanizer(config={"sensors": cfg_over} if cfg_over else None, seed=seed)
        rows = h.sensors.generate(mode=mode, fs=fs, duration=duration)
        stats = h.sensors.stats(rows)
        is_dead = h.sensors.is_dead(rows)
        series = {
            "t": _downsample([r["t"] for r in rows]),
            "acc_x": _downsample([r["acc"][0] for r in rows]),
            "acc_y": _downsample([r["acc"][1] for r in rows]),
            "acc_z": _downsample([r["acc"][2] for r in rows]),
            "gyro_x": _downsample([r["gyro"][0] for r in rows]),
            "gyro_y": _downsample([r["gyro"][1] for r in rows]),
            "gyro_z": _downsample([r["gyro"][2] for r in rows]),
        }
        self._json({
            "ok": True,
            "mode": mode,
            "fs": fs,
            "duration": duration,
            "sample_count": len(rows),
            "series": series,
            "stats": stats,
            "is_dead": is_dead,
        })

    # ---------- /api/sensors/csv ----------

    def _api_sensors_csv(self, body: dict) -> None:
        mode, fs, duration, seed = _sensor_request(body)
        cfg_over = _sensors_cfg(body)
        h = Humanizer(config={"sensors": cfg_over} if cfg_over else None, seed=seed)
        rows = h.sensors.generate(mode=mode, fs=fs, duration=duration)

        # Build the CSV in memory, then send.
        # 在内存中构造 CSV 后发送。
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["t", "acc_x", "acc_y", "acc_z",
                    "lin_x", "lin_y", "lin_z",
                    "gyro_x", "gyro_y", "gyro_z",
                    "mag_x", "mag_y", "mag_z"])
        for r in rows:
            w.writerow([r["t"], *r["acc"], *r["lin"], *r["gyro"], *r["mag"]])
        data = buf.getvalue().encode("utf-8")
        self._send(200, data, "text/csv; charset=utf-8", {
            "Content-Disposition": f'attachment; filename="sensors_{mode}.csv"',
        })


# ---------------------------------------------------------------- Server


class _Server(ThreadingHTTPServer):
    # Windows: allow_reuse_address can steal an in-use port; keep it off.
    # Windows：allow_reuse_address 会抢占已占用端口，保持关闭。
    allow_reuse_address = False


def make_server(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    # The interactive API has no authentication; it must stay on IPv4 loopback.
    # 交互式 API 没有认证，因此只允许绑定 IPv4 回环地址。
    try:
        address = ipaddress.ip_address(host)
    except ValueError as exc:
        raise ValueError("Web UI 仅允许绑定 127.0.0.1") from exc
    if address.version != 4 or not address.is_loopback:
        raise ValueError("Web UI 仅允许绑定 127.0.0.1")
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
        raise ValueError("port 必须是 0-65535 的整数")
    httpd = _Server((str(address), port), Handler)
    httpd.daemon_threads = True
    return httpd


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="touch-humanization Web UI")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args(argv)

    httpd = make_server(args.host, args.port)
    host, port = httpd.server_address[0], httpd.server_address[1]
    url = f"http://{host}:{port}/"
    print(f"touch-humanization Web UI: {url}")
    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
