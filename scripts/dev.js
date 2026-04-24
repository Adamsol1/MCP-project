const { spawn, spawnSync } = require("node:child_process");

const npm = process.platform === "win32" ? "npm.cmd" : "npm";

const services = [
  {
    key: "mcp",
    name: "Generation MCP",
    args: ["--silent", "run", "dev:mcp"],
    success: [/Starting Generation MCP on (.+)/, /Generation MCP already running on (.+)/],
  },
  {
    key: "review",
    name: "Review MCP",
    args: ["--silent", "run", "dev:review"],
    success: [/Starting Review MCP on (.+)/, /Review MCP already running on (.+)/],
  },
  {
    key: "council",
    name: "Council MCP",
    args: ["--silent", "run", "dev:council"],
    success: [/Starting Council MCP on (.+)/, /Council MCP already running on (.+)/],
  },
  {
    key: "backend",
    name: "Backend API",
    args: ["--silent", "run", "dev:backend"],
    success: [/Backend API started successfully: (.+)/, /Backend API already running on (.+)/],
  },
  {
    key: "frontend",
    name: "Frontend",
    args: ["--silent", "run", "dev:frontend"],
    success: [/Local:\s+(http:\/\/localhost:\d+\/)/],
  },
];

const children = new Map();
const startedServices = new Set();
let shuttingDown = false;

const BARBOSA_BANNER = [
  " ____            _                     ",
  "| __ )  __ _ _ __| |__   ___  ___  __ _",
  "|  _ \\ / _ | '__| '_ \\ / _ \\/ __|/ _ |",
  "| |_) | (_| | |  | |_) | (_) \\__ \\ (_| |",
  "|____/ \\__,_|_|  |_.__/ \\___/|___/\\__,_|",
].join("\n");

function terminalLink(url) {
  return `\x1b[94m\x1b]8;;${url}\x1b\\${url}\x1b]8;;\x1b\\\x1b[0m`;
}

function maybePrintBanner(service) {
  startedServices.add(service.key);
  if (startedServices.size === services.length) {
    console.log(BARBOSA_BANNER);
  }
}

function stripAnsi(text) {
  return text.replace(/\x1b\[[0-9;]*m/g, "");
}

function normalizeLine(line) {
  return stripAnsi(line).replace(/[ \t]+$/g, "");
}

function dependencyMessage(service, line) {
  const match = line.match(/Missing Python dependency '([^']+)' in ([^.]+)\./);
  if (!match) return null;
  return `${service.name} failed: missing Python dependency '${match[1]}'. Run 'cd ${match[2]} && poetry install'.`;
}

function portMessage(service, line) {
  const match = line.match(/(.+ port \d+ is already in use\..+)/);
  if (!match) return null;
  return `${service.name} failed: ${match[1]}`;
}

function shouldForwardRuntimeLine(state, line) {
  if (state.forwardLines > 0) {
    state.forwardLines -= 1;
    return true;
  }

  if (/Traceback|Exception|Error:|ERROR|WARN|WARNING|CRITICAL|failed|Cannot|Invalid/i.test(line)) {
    if (/Traceback/i.test(line)) {
      state.forwardLines = 12;
    }
    return true;
  }

  return false;
}

function handleLine(service, state, rawLine) {
  const line = normalizeLine(rawLine);
  if (!line) return;

  for (const pattern of service.success) {
    const match = line.match(pattern);
    if (match && !state.reported) {
      state.reported = true;
      const target = service.key === "frontend" ? terminalLink(match[1]) : match[1];
      console.log(`${service.name} started successfully: ${target}`);
      maybePrintBanner(service);
      return;
    }
  }

  const failure = dependencyMessage(service, line) || portMessage(service, line);
  if (failure && !state.reportedFailure) {
    state.reportedFailure = true;
    console.error(failure);
    return;
  }

  if (shouldForwardRuntimeLine(state, line)) {
    console.error(`[${service.key}] ${line}`);
  }
}

function attachOutput(stream, service, state) {
  let buffer = "";
  stream.on("data", (chunk) => {
    buffer += chunk.toString();
    const lines = buffer.split(/\r?\n/);
    buffer = lines.pop() || "";
    for (const line of lines) {
      handleLine(service, state, line);
    }
  });
  stream.on("end", () => {
    if (buffer) {
      handleLine(service, state, buffer);
    }
  });
}

function startService(service) {
  const state = { reported: false, reportedFailure: false, forwardLines: 0 };
  const child = spawn(npm, service.args, {
    cwd: process.cwd(),
    stdio: ["ignore", "pipe", "pipe"],
    shell: process.platform === "win32",
    windowsHide: true,
  });

  children.set(service.key, child);
  attachOutput(child.stdout, service, state);
  attachOutput(child.stderr, service, state);

  child.on("exit", (code, signal) => {
    children.delete(service.key);
    if (shuttingDown || signal) return;
    if (code !== 0 && !state.reportedFailure) {
      const action = state.reported ? "stopped unexpectedly" : "failed to start";
      console.error(`${service.name} ${action} (exit code ${code}).`);
    }
  });
}

function shutdown() {
  if (shuttingDown) return;
  shuttingDown = true;
  for (const child of children.values()) {
    if (child.killed) {
      continue;
    }
    if (process.platform === "win32") {
      spawnSync("taskkill", ["/PID", String(child.pid), "/T", "/F"], {
        stdio: "ignore",
        windowsHide: true,
      });
    } else {
      child.kill();
    }
  }
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
process.on("exit", shutdown);

for (const service of services) {
  startService(service);
}
