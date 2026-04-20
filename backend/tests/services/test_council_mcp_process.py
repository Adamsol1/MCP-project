import json

import pytest

from src.services import council_mcp_process


class FakeProcess:
    def __init__(self):
        self.returncode = None
        self.terminated = False
        self.killed = False
        self.wait_calls = 0

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True
        self.returncode = -9

    def wait(self):
        self.wait_calls += 1
        self.returncode = 0
        return self.returncode


@pytest.mark.asyncio
async def test_maybe_start_council_mcp_uses_sync_popen(monkeypatch):
    launched = {}
    fake_process = FakeProcess()

    def fake_popen(args, cwd, env):
        launched["args"] = args
        launched["cwd"] = cwd
        launched["env"] = env
        return fake_process

    async def fake_wait_for_health(_server_url):
        return True

    monkeypatch.setattr(council_mcp_process, "_health_ok", lambda _server_url: False)
    monkeypatch.setattr(council_mcp_process, "_wait_for_health", fake_wait_for_health)
    monkeypatch.setattr(council_mcp_process.shutil, "which", lambda _cmd: "poetry.exe")
    monkeypatch.setattr(council_mcp_process.subprocess, "Popen", fake_popen)

    process = await council_mcp_process.maybe_start_council_mcp(
        "http://127.0.0.1:8003/sse"
    )

    assert process is fake_process
    assert launched["args"] == [
        "poetry.exe",
        "run",
        "python",
        "server_http.py",
    ]
    assert launched["cwd"].endswith("council_mcp")
    assert launched["env"]["COUNCIL_MCP_PORT"] == "8003"


def test_health_ok_requires_council_identity(monkeypatch):
    class FakeResponse:
        status = 200

        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self, _limit):
            return json.dumps(self.payload).encode("utf-8")

    monkeypatch.setattr(
        council_mcp_process,
        "urlopen",
        lambda _url, **_kwargs: FakeResponse({"status": "ok"}),
    )

    assert council_mcp_process._health_ok("http://127.0.0.1:8003/sse") is False

    monkeypatch.setattr(
        council_mcp_process,
        "urlopen",
        lambda _url, **_kwargs: FakeResponse(
            {"status": "ok", "server": "council"}
        ),
    )

    assert council_mcp_process._health_ok("http://127.0.0.1:8003/sse") is True


@pytest.mark.asyncio
async def test_stop_council_mcp_terminates_and_waits(monkeypatch):
    fake_process = FakeProcess()
    monkeypatch.setattr(council_mcp_process.sys, "platform", "linux")

    await council_mcp_process.stop_council_mcp(fake_process)

    assert fake_process.terminated is True
    assert fake_process.killed is False
    assert fake_process.wait_calls == 1
    assert fake_process.returncode == 0
