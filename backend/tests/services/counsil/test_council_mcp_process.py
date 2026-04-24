import pytest

from src.services.council import council_mcp_process


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

    def fake_popen(args, cwd):
        launched["args"] = args
        launched["cwd"] = cwd
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
    assert launched["cwd"].endswith("council_mcp_server")


@pytest.mark.asyncio
async def test_stop_council_mcp_terminates_and_waits(monkeypatch):
    fake_process = FakeProcess()
    monkeypatch.setattr(council_mcp_process.sys, "platform", "linux")

    await council_mcp_process.stop_council_mcp(fake_process)

    assert fake_process.terminated is True
    assert fake_process.killed is False
    assert fake_process.wait_calls == 1
    assert fake_process.returncode == 0
