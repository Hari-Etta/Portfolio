from fastapi.testclient import TestClient

H = {"x-proxy-secret": "test-proxy-secret"}


def _client(monkeypatch):
    import api_server

    monkeypatch.setattr(api_server, "chat_turn", lambda q, memory=None: {"answer_markdown": "ok", "mode": "help", "memory": {}})
    api_server._rate_counters.clear()
    return TestClient(api_server.app)


def test_ping(monkeypatch):
    assert _client(monkeypatch).get("/api/ping").json() == {"ok": True}


def test_chat_requires_proxy_secret(monkeypatch):
    c = _client(monkeypatch)
    assert c.post("/api/chat", json={"query": "hi"}).status_code == 403
    r = c.post("/api/chat", json={"query": "hi", "conversation_id": "s1"}, headers=H)
    assert r.status_code == 200 and r.json()["conversation_id"] == "s1"


def test_rate_limit_is_per_client_ip(monkeypatch):
    c = _client(monkeypatch)
    for _ in range(3):
        assert c.post("/api/chat", json={"query": "hi"}, headers={**H, "x-client-ip": "1.1.1.1"}).status_code == 200
    assert c.post("/api/chat", json={"query": "hi"}, headers={**H, "x-client-ip": "1.1.1.1"}).status_code == 429
    # a different visitor is unaffected
    assert c.post("/api/chat", json={"query": "hi"}, headers={**H, "x-client-ip": "2.2.2.2"}).status_code == 200


def test_feedback_listing_is_admin_only(monkeypatch):
    c = _client(monkeypatch)
    assert c.get("/api/feedback").status_code == 401
    assert c.get("/api/feedback", headers={"authorization": "Bearer wrong"}).status_code == 401
