# -*- coding: utf-8 -*-
import json
import threading
import urllib.error
import urllib.request

import pytest

from touch_humanization.web.server import make_server


@pytest.fixture()
def server():
    httpd = make_server("127.0.0.1", 0)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{port}"
    httpd.shutdown()
    httpd.server_close()


def _post(url, body):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def test_health_and_index(server):
    with urllib.request.urlopen(server + "/api/health", timeout=5) as r:
        assert json.loads(r.read())["ok"] is True
    with urllib.request.urlopen(server + "/", timeout=5) as r:
        assert b"touch-humanization" in r.read()


def test_gesture_endpoint(server):
    r = _post(server + "/api/gesture", {
        "start": [100, 1800], "end": [900, 400], "seed": 42,
    })
    assert r["ok"] is True
    g = r["gesture"]
    assert g["points"][0] == [100, 1800]
    assert g["points"][-1] == [900, 400]
    assert len(g["intervals"]) == len(g["points"]) - 1


def test_gesture_seed_reproducible(server):
    body = {"start": [0, 0], "end": [500, 500], "seed": 7}
    a = _post(server + "/api/gesture", body)["gesture"]
    b = _post(server + "/api/gesture", body)["gesture"]
    assert a == b


def test_gesture_bad_body(server):
    req = urllib.request.Request(server + "/api/gesture", data=b"not json",
                                 method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=5)
    except urllib.error.HTTPError as e:
        assert e.code == 400
    else:
        raise AssertionError("应返回 400")
