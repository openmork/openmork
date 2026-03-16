from openmork_cli.llm_gateway import LLMGateway


def _base_config():
    return {
        "policy": {
            "cooldown_seconds": 10,
            "quarantine_seconds": 100,
        },
        "providers": [
            {
                "id": "p1",
                "provider": "openrouter",
                "base_url": "https://openrouter.ai/api/v1",
                "api_key_env": "GW_KEY_1",
                "models": ["*"],
                "weight": 1,
                "cost_tier": 1,
                "latency_tier": 1,
            },
            {
                "id": "p2",
                "provider": "zai",
                "base_url": "https://api.z.ai/api/paas/v4",
                "api_key_env": "GW_KEY_2",
                "models": ["*"],
                "weight": 1,
                "cost_tier": 2,
                "latency_tier": 2,
            },
        ],
    }


def test_selection_initial(monkeypatch):
    monkeypatch.setenv("GW_KEY_1", "k1")
    monkeypatch.setenv("GW_KEY_2", "k2")

    now = [0.0]
    gw = LLMGateway(_base_config(), now_fn=lambda: now[0])

    first = gw.resolve_gateway_route("", "any/model")
    second = gw.resolve_gateway_route("", "any/model")

    assert first is not None
    assert second is not None
    assert {first["route_id"], second["route_id"]} == {"p1", "p2"}


def test_sticky_by_conversation(monkeypatch):
    monkeypatch.setenv("GW_KEY_1", "k1")
    monkeypatch.setenv("GW_KEY_2", "k2")

    now = [0.0]
    gw = LLMGateway(_base_config(), now_fn=lambda: now[0])

    r1 = gw.resolve_gateway_route("conv-1", "model-x")
    r2 = gw.resolve_gateway_route("conv-1", "model-x")

    assert r1 is not None
    assert r2 is not None
    assert r1["route_id"] == r2["route_id"]
    assert r2["sticky"] is True


def test_quarantine_on_401(monkeypatch):
    monkeypatch.setenv("GW_KEY_1", "k1")
    monkeypatch.setenv("GW_KEY_2", "k2")

    now = [0.0]
    gw = LLMGateway(_base_config(), now_fn=lambda: now[0])

    r = gw.resolve_gateway_route("", "m")
    assert r is not None

    gw.report_route_result(r["route_id"], 401)
    st = gw.get_route_state(r["route_id"])
    assert st is not None
    assert st.quarantined_until == 100.0

    other = gw.resolve_gateway_route("", "m")
    assert other is not None
    assert other["route_id"] != r["route_id"]


def test_cooldown_429_and_recovery(monkeypatch):
    monkeypatch.setenv("GW_KEY_1", "k1")
    monkeypatch.setenv("GW_KEY_2", "k2")

    now = [0.0]
    gw = LLMGateway(_base_config(), now_fn=lambda: now[0])

    r = gw.resolve_gateway_route("", "m")
    assert r is not None

    gw.report_route_result(r["route_id"], 429)
    st = gw.get_route_state(r["route_id"])
    assert st is not None
    assert st.cooldown_until == 10.0

    during = gw.resolve_gateway_route("", "m")
    assert during is not None
    assert during["route_id"] != r["route_id"]

    now[0] = 11.0
    after = gw.resolve_gateway_route("", "m")
    assert after is not None
    assert after["route_id"] in {"p1", "p2"}
