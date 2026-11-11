# -*- coding: utf-8 -*-
# Web UI unit tests (stdlib http.server).
# Web UI 单元测试（stdlib http.server）。
import json
import threading
import urllib.error
import urllib.request

import pytest

from touch_humanization.web.server import make_server


@pytest.fixture()
def server():
    # Start a server on a free port; yield base URL; shut down after.
    # 在空闲端口启动服务；产出 base URL；结束后关闭。
    httpd = make_server("127.0.0.1", 0)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{port}"
    httpd.shutdown()
    httpd.server_close()


def _post(url, body):
    # POST JSON and parse JSON response.
    # 发送 JSON POST 并解析 JSON 响应。
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def test_health_and_index(server):
    # /api/health must be ok; / must contain the three tab anchors.
    # /api/health 必须 ok；/ 必须包含三个 tab 锚点。
    with urllib.request.urlopen(server + "/api/health", timeout=5) as r:
        assert json.loads(r.read())["ok"] is True
    with urllib.request.urlopen(server + "/", timeout=5) as r:
        body = r.read()
    assert b"touch-humanization" in body
    assert b"tab-kinematics" in body
    assert b"tab-timing" in body
    assert b"tab-sensors" in body


# ------------------------------------------------------------ kinematics
# ------------------------------------------------------------ 手势轨迹

def test_gesture_basic(server):
    # Basic gesture: exact endpoints and interval count.
    # 基础轨迹：端点精确、间隔数正确。
    r = _post(server + "/api/gesture", {
        "start": [100, 1800], "end": [900, 400], "seed": 42,
    })
    g = r["gesture"]
    assert g["points"][0] == [100, 1800]
    assert g["points"][-1] == [900, 400]
    assert len(g["intervals"]) == len(g["points"]) - 1


def test_gesture_seed_reproducible(server):
    # Same seed -> identical gesture.
    # 同 seed -> 轨迹一致。
    body = {"start": [0, 0], "end": [500, 500], "seed": 7}
    a = _post(server + "/api/gesture", body)["gesture"]
    b = _post(server + "/api/gesture", body)["gesture"]
    assert a == b


def test_gesture_slider_mode(server):
    # Slider mode flag and exact end.
    # 滑块模式标志与终点精确。
    r = _post(server + "/api/gesture", {
        "start": [80, 1500], "end": [1200, 1500],
        "seed": 1, "for_slider": True,
    })
    g = r["gesture"]
    assert g["for_slider"] is True
    assert g["points"][-1] == [1200, 1500]


def test_gesture_advanced_params(server):
    # Fixed step count must be honored.
    # 固定步数必须被遵守。
    r = _post(server + "/api/gesture", {
        "start": [0, 0], "end": [500, 0],
        "seed": 3,
        "steps_min": 40, "steps_max": 40,
        "overshoot_prob": 0,   # no pull-back points / 关闭过冲，避免回拉点干扰步数
    })
    assert r["gesture"]["steps"] == 40


def test_gesture_bad_body(server):
    # Malformed JSON body must be rejected with 400.
    # 非法 JSON 请求体必须返回 400。
    req = urllib.request.Request(server + "/api/gesture", data=b"not json",
                                 method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=5)
    except urllib.error.HTTPError as e:
        assert e.code == 400
    else:
        raise AssertionError("应返回 400 / 400 expected")


def test_rejects_non_loopback_bind():
    # The unauthenticated API must never bind to a LAN/public interface.
    # 无认证 API 不得绑定到局域网或公网网卡。
    with pytest.raises(ValueError, match="127.0.0.1"):
        make_server("0.0.0.0", 0)


def test_rejects_invalid_host_header(server):
    # DNS-rebinding / foreign Host headers must not reach the API.
    # 外部 Host 不得访问本地服务。
    req = urllib.request.Request(server + "/api/health", headers={"Host": "attacker.example"})
    try:
        urllib.request.urlopen(req, timeout=5)
    except urllib.error.HTTPError as exc:
        assert exc.code == 403
    else:
        raise AssertionError("expected 403 for invalid Host")


def test_post_requires_json_content_type(server):
    # Non-JSON request bodies are rejected explicitly.
    # 非 JSON 请求体必须被明确拒绝。
    req = urllib.request.Request(
        server + "/api/gesture", data=b"{}",
        method="POST", headers={"Content-Type": "text/plain"},
    )
    try:
        urllib.request.urlopen(req, timeout=5)
    except urllib.error.HTTPError as exc:
        assert exc.code == 415
    else:
        raise AssertionError("expected 415 for non-JSON content type")


def test_post_requires_json_object(server):
    # JSON arrays are not valid API request objects.
    # JSON 数组不是合法的 API 请求对象。
    req = urllib.request.Request(
        server + "/api/gesture", data=b"[]",
        method="POST", headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=5)
    except urllib.error.HTTPError as exc:
        assert exc.code == 400
    else:
        raise AssertionError("expected 400 for a non-object JSON body")


def test_post_rejects_oversized_body(server):
    # Oversized requests must be rejected before JSON decoding.
    # 超大请求体必须在 JSON 解码前拒绝。
    from touch_humanization.web.server import MAX_REQUEST_BODY
    req = urllib.request.Request(
        server + "/api/gesture", data=b" " * (MAX_REQUEST_BODY + 1),
        method="POST", headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=5)
    except urllib.error.HTTPError as exc:
        assert exc.code == 413
    else:
        raise AssertionError("expected 413 for oversized body")


def test_wake_window_rejects_invalid_time(server):
    # Invalid time strings must not silently become midnight.
    # 无效时间不得静默回退成午夜。
    req = urllib.request.Request(
        server + "/api/timing/window",
        data=json.dumps({"wake_window": {"start": "25:90", "end": "23:00"}}).encode(),
        method="POST", headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=5)
    except urllib.error.HTTPError as exc:
        assert exc.code == 400
    else:
        raise AssertionError("expected 400 for invalid HH:MM")


def test_sensor_generation_has_resource_bounds(server):
    # Sampling must be finite and bounded before rows are allocated.
    # 必须在分配数据前限制传感器采样规模。
    req = urllib.request.Request(
        server + "/api/sensors/generate",
        data=json.dumps({"fs": 500, "duration": 61}).encode(),
        method="POST", headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=5)
    except urllib.error.HTTPError as exc:
        assert exc.code == 400
    else:
        raise AssertionError("expected 400 for oversized sensor request")


# ------------------------------------------------------------ timing
# ------------------------------------------------------------ 时序

def test_timing_sample(server):
    # Sample distribution endpoints and stats.
    # 采样分布的端点与统计。
    r = _post(server + "/api/timing/sample", {
        "n": 500, "lo": 0.5, "hi": 2.0, "lognormal": True, "seed": 42,
    })
    assert len(r["samples"]) == 500
    assert all(0.5 <= v <= 2.0 for v in r["samples"])
    assert r["stats"]["n"] == 500
    assert len(r["bins"]) > 0


def test_timing_sample_reproducible(server):
    # Same seed -> identical samples.
    # 同 seed -> 采样一致。
    body = {"n": 200, "lo": 0.5, "hi": 2.0, "lognormal": True, "seed": 9}
    a = _post(server + "/api/timing/sample", body)["samples"]
    b = _post(server + "/api/timing/sample", body)["samples"]
    assert a == b


def test_timing_window_simple(server):
    # Simple window: one segment, no cross-midnight.
    # 普通窗口：单段、非跨午夜。
    r = _post(server + "/api/timing/window", {
        "wake_window": {"start": "07:30", "end": "23:00"},
    })
    assert r["start_min"] == 7 * 60 + 30
    assert r["end_min"] == 23 * 60
    assert r["cross_midnight"] is False
    assert r["segments"] == [[450, 1380]]


def test_timing_window_cross_midnight(server):
    # Cross-midnight window: two segments.
    # 跨午夜窗口：两段。
    r = _post(server + "/api/timing/window", {
        "wake_window": {"start": "20:00", "end": "06:00"},
    })
    assert r["cross_midnight"] is True
    assert r["segments"] == [[1200, 1440], [0, 360]]


def test_timing_cooldown(server):
    # Cooldown triggers every N taps.
    # 冷却每 N 次点击触发一次。
    r = _post(server + "/api/timing/cooldown", {
        "n": 30, "cooldown_every": 10, "cooldown_seconds": 5.0, "seed": 1,
    })
    assert r["n"] == 30
    assert len(r["events"]) == 30
    cds = [ev for ev in r["events"] if ev["cooldown"] is not None]
    assert len(cds) == 3
    assert all(3.5 <= ev["cooldown"] <= 6.5 for ev in cds)


# ------------------------------------------------------------ sensors
# ------------------------------------------------------------ 传感器

def test_sensors_generate_alive(server):
    # All modes must be reported alive.
    # 所有模式必须报告为活着。
    for mode in ("resting", "walking", "tapping", "scrolling"):
        r = _post(server + "/api/sensors/generate", {
            "mode": mode, "fs": 100, "duration": 2.0, "seed": 42,
        })
        assert r["is_dead"] is False, mode
        assert r["sample_count"] == 200
        assert len(r["series"]["t"]) > 0


def test_sensors_generate_reproducible(server):
    # Same seed -> identical series.
    # 同 seed -> 序列一致。
    body = {"mode": "walking", "fs": 50, "duration": 1.0, "seed": 11}
    a = _post(server + "/api/sensors/generate", body)["series"]
    b = _post(server + "/api/sensors/generate", body)["series"]
    assert a == b


def test_sensors_csv_content(server):
    # CSV content type, header, and row count.
    # CSV 内容类型、表头与行数。
    req = urllib.request.Request(
        server + "/api/sensors/csv",
        data=json.dumps({"mode": "walking", "fs": 50, "duration": 1.0, "seed": 1})
        .encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        ctype = r.headers.get("Content-Type", "")
        body = r.read().decode("utf-8")
    assert "text/csv" in ctype
    assert body.startswith("t,acc_x")
    lines = body.strip().splitlines()
    assert len(lines) == 1 + 50
