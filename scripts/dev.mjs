import { spawn } from "node:child_process";

const colors = {
  backend: "\x1b[36m",
  frontend: "\x1b[35m",
  reset: "\x1b[0m",
};

const processes = [
  {
    name: "backend",
    command: "bash",
    args: ["scripts/dev-backend.sh"],
    color: colors.backend,
  },
  {
    name: "frontend",
    command: "npm",
    args: ["--prefix", "frontend", "run", "dev"],
    color: colors.frontend,
  },
];

const children = new Set();
let shuttingDown = false;

function prefixOutput(stream, name, color, target) {
  let pending = "";

  stream.on("data", (chunk) => {
    pending += chunk.toString();
    const lines = pending.split(/\r?\n/);
    pending = lines.pop() ?? "";

    for (const line of lines) {
      target.write(`${color}[${name}]${colors.reset} ${line}\n`);
    }
  });

  stream.on("end", () => {
    if (pending) {
      target.write(`${color}[${name}]${colors.reset} ${pending}\n`);
    }
  });
}

function stopAll(signal = "SIGTERM") {
  if (shuttingDown) {
    return;
  }
  shuttingDown = true;

  for (const child of children) {
    if (child.exitCode !== null || child.signalCode !== null) {
      continue;
    }

    try {
      if (process.platform === "win32") {
        child.kill(signal);
      } else {
        process.kill(-child.pid, signal);
      }
    } catch {
      child.kill(signal);
    }
  }
}

for (const proc of processes) {
  const child = spawn(proc.command, proc.args, {
    cwd: process.cwd(),
    env: process.env,
    detached: process.platform !== "win32",
    stdio: ["inherit", "pipe", "pipe"],
  });

  children.add(child);
  prefixOutput(child.stdout, proc.name, proc.color, process.stdout);
  prefixOutput(child.stderr, proc.name, proc.color, process.stderr);

  child.on("exit", (code, signal) => {
    children.delete(child);
    if (!shuttingDown && code !== 0) {
      console.error(
        `${proc.color}[${proc.name}]${colors.reset} exited with ${signal ?? `code ${code}`}`,
      );
      stopAll();
      process.exitCode = code ?? 1;
    }
  });
}

process.on("SIGINT", () => {
  stopAll("SIGINT");
  setTimeout(() => process.exit(130), 100);
});

process.on("SIGTERM", () => {
  stopAll("SIGTERM");
  setTimeout(() => process.exit(143), 100);
});
