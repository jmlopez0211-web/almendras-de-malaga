import test, { before, after } from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import net from "node:net";
import { createHmac } from "node:crypto";

let child;
let baseUrl;
let output = "";

async function freePort() {
  const probe = net.createServer();
  await new Promise((resolve, reject) => {
    probe.once("error", reject);
    probe.listen(0, "127.0.0.1", resolve);
  });
  const { port } = probe.address();
  await new Promise(resolve => probe.close(resolve));
  return port;
}

before(async () => {
  const port = await freePort();
  baseUrl = `http://127.0.0.1:${port}`;
  child = spawn(process.execPath, ["server.js"], {
    cwd: process.cwd(),
    env: {
      ...process.env,
      PORT: String(port),
      OPENAI_API_KEY: "",
      WHATSAPP_ACCESS_TOKEN: "",
      WHATSAPP_PHONE_NUMBER_ID: "",
      WHATSAPP_VERIFY_TOKEN: "test-verify-token",
      WHATSAPP_APP_SECRET: "test-app-secret",
      WHATSAPP_API_VERSION: ""
    },
    stdio: ["ignore", "pipe", "pipe"]
  });
  child.stdout.on("data", chunk => { output += chunk.toString(); });
  child.stderr.on("data", chunk => { output += chunk.toString(); });

  const deadline = Date.now() + 10000;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) throw new Error("Assistant server exited: " + output);
    try {
      const response = await fetch(baseUrl + "/health");
      if (response.ok) return;
    } catch {}
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw new Error("Assistant server did not start: " + output);
});

after(async () => {
  if (!child || child.exitCode !== null) return;
  child.kill("SIGTERM");
  await new Promise(resolve => {
    const timeout = setTimeout(() => {
      child.kill("SIGKILL");
      resolve();
    }, 3000);
    child.once("exit", () => {
      clearTimeout(timeout);
      resolve();
    });
  });
});

test("health endpoint exposes service status without leaking secrets", async () => {
  const response = await fetch(baseUrl + "/health");
  const data = await response.json();
  assert.equal(response.status, 200);
  assert.equal(data.ok, true);
  assert.equal(data.service, "almendras-assistant");
  assert.equal(data.aiConfigured, false);
  assert.equal(data.whatsappConfigured, false);
  assert.equal(JSON.stringify(data).includes("test-verify-token"), false);
});

test("chat endpoint enforces allowed browser origins", async () => {
  const response = await fetch(baseUrl + "/api/chat", {
    method: "POST",
    headers: { Origin: "https://evil.example", "Content-Type": "application/json" },
    body: JSON.stringify({ message: "Hola", session_id: "0123456789abcdef" })
  });
  assert.equal(response.status, 403);
});

test("chat endpoint supports a restricted CORS preflight", async () => {
  const response = await fetch(baseUrl + "/api/chat", {
    method: "OPTIONS",
    headers: { Origin: "https://jmlopez0211-web.github.io" }
  });
  assert.equal(response.status, 204);
  assert.equal(response.headers.get("access-control-allow-origin"), "https://jmlopez0211-web.github.io");
  assert.match(response.headers.get("access-control-allow-methods"), /POST/);
});

test("chat endpoint rejects non-JSON requests", async () => {
  const response = await fetch(baseUrl + "/api/chat", {
    method: "POST",
    headers: { "Content-Type": "text/plain" },
    body: "Hola"
  });
  assert.equal(response.status, 415);
});

test("chat endpoint returns a controlled 400 for malformed JSON", async () => {
  const response = await fetch(baseUrl + "/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{invalid"
  });
  assert.equal(response.status, 400);
  assert.deepEqual(await response.json(), { error: "JSON inválido" });
});

test("chat endpoint validates body shape, message length and session identifiers", async () => {
  const invalidBodies = [
    "[]",
    JSON.stringify({ message: "Hola", session_id: "short" }),
    JSON.stringify({ message: "x".repeat(2001), session_id: "0123456789abcdef" }),
    JSON.stringify({ message: "Hola", session_id: "0123456789abcdef", extra: "allowed" })
  ];
  for (const body of invalidBodies) {
    const response = await fetch(baseUrl + "/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body
    });
    assert.equal(response.status, 400);
  }
});

test("chat endpoint rejects oversized bodies without terminating the server", async () => {
  const response = await fetch(baseUrl + "/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: "x".repeat(17000), session_id: "0123456789abcdef" })
  });
  assert.equal(response.status, 413);
  const health = await fetch(baseUrl + "/health");
  assert.equal(health.status, 200);
});

test("rate limiting uses the trusted rightmost forwarded address and returns 429", async () => {
  let last;
  for (let i = 0; i < 31; i++) {
    last = await fetch(baseUrl + "/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Forwarded-For": "spoof-" + i + ", 198.51.100.77"
      },
      body: "{invalid"
    });
  }
  assert.equal(last.status, 429);
});

test("valid chat requests fail closed when the AI provider is not configured", async () => {
  const response = await fetch(baseUrl + "/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json", Origin: "https://jmlopez0211-web.github.io" },
    body: JSON.stringify({ message: "Hola", session_id: "0123456789abcdef" })
  });
  assert.equal(response.status, 503);
  assert.equal((await response.json()).mode, "fallback");
});

test("WhatsApp webhook verification requires the configured verify token", async () => {
  const good = await fetch(baseUrl + "/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=test-verify-token&hub.challenge=abc123");
  assert.equal(good.status, 200);
  assert.equal(await good.text(), "abc123");
  const bad = await fetch(baseUrl + "/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=wrong&hub.challenge=abc123");
  assert.equal(bad.status, 403);
});

test("WhatsApp webhook rejects unsigned and malformed events", async () => {
  const unsigned = await fetch(baseUrl + "/webhook/whatsapp", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ entry: [] })
  });
  assert.equal(unsigned.status, 401);
});


test("WhatsApp webhook accepts a correctly signed, structurally valid event", async () => {
  const raw = JSON.stringify({ entry: [] });
  const signature = "sha256=" + createHmac("sha256", "test-app-secret").update(raw).digest("hex");
  const response = await fetch(baseUrl + "/webhook/whatsapp", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Hub-Signature-256": signature },
    body: raw
  });
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { received: true });
});

test("WhatsApp webhook rejects signed malformed JSON", async () => {
  const raw = "{invalid";
  const signature = "sha256=" + createHmac("sha256", "test-app-secret").update(raw).digest("hex");
  const response = await fetch(baseUrl + "/webhook/whatsapp", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Hub-Signature-256": signature },
    body: raw
  });
  assert.equal(response.status, 400);
});
