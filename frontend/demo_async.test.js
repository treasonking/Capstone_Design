const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const html = fs.readFileSync(path.join(__dirname, "demo.html"), "utf8");
const scriptMatch = html.match(/<script>([\s\S]*?)<\/script>/);
assert.ok(scriptMatch, "demo.html must contain an inline script");
const demoScript = scriptMatch[1];

class FakeClassList {
  constructor() {
    this.values = new Set();
  }

  add(...names) {
    names.forEach((name) => this.values.add(name));
  }

  remove(...names) {
    names.forEach((name) => this.values.delete(name));
  }

  toggle(name, force) {
    const enabled = force === undefined ? !this.values.has(name) : Boolean(force);
    if (enabled) this.values.add(name);
    else this.values.delete(name);
    return enabled;
  }
}

class FakeElement {
  constructor(id = "") {
    this.id = id;
    this.value = "";
    this.textContent = "";
    this.className = "";
    this.hidden = false;
    this.disabled = false;
    this.required = false;
    this.type = "text";
    this.autocomplete = "";
    this.dataset = {};
    this.style = {};
    this.children = [];
    this.listeners = new Map();
    this.attributes = new Map();
    this.classList = new FakeClassList();
    this.span = null;
  }

  addEventListener(type, callback) {
    const callbacks = this.listeners.get(type) || [];
    callbacks.push(callback);
    this.listeners.set(type, callbacks);
  }

  async emit(type, event = {}) {
    const completeEvent = {
      preventDefault() {},
      target: this,
      ...event,
    };
    const results = (this.listeners.get(type) || []).map((callback) => callback(completeEvent));
    await Promise.all(results);
  }

  setAttribute(name, value) {
    this.attributes.set(name, String(value));
  }

  replaceChildren(...children) {
    this.children = children;
  }

  append(...children) {
    this.children.push(...children);
  }

  querySelector(selector) {
    if (selector === "span") {
      if (!this.span) this.span = new FakeElement(`${this.id}-span`);
      return this.span;
    }
    if (selector === "[data-switch]") {
      return this.children.find((child) => child && child.dataset && child.dataset.switch) || null;
    }
    return null;
  }

  closest(selector) {
    return selector === "[data-switch]" && this.dataset.switch ? this : null;
  }

  reset() {}
  focus() {}
}

class FakeStorage {
  constructor(initial = {}) {
    this.values = new Map(Object.entries(initial));
  }

  getItem(key) {
    return this.values.has(key) ? this.values.get(key) : null;
  }

  setItem(key, value) {
    this.values.set(key, String(value));
  }

  removeItem(key) {
    this.values.delete(key);
  }
}

function createHarness({ storage = {}, fetchImpl } = {}) {
  const elements = new Map();
  const element = (id) => {
    if (!elements.has(id)) elements.set(id, new FakeElement(id));
    return elements.get(id);
  };
  const sessionStorage = new FakeStorage(storage);
  let currentFetch = fetchImpl || (() => Promise.reject(new Error("unexpected fetch")));
  const context = vm.createContext({
    AbortController,
    DOMException,
    URL,
    console,
    document: {
      getElementById: element,
      createElement: () => new FakeElement(),
      querySelectorAll: () => [],
    },
    fetch: (...args) => currentFetch(...args),
    sessionStorage,
    window: {
      clearTimeout,
      confirm: () => true,
      scrollTo() {},
      setTimeout,
    },
  });

  element("authApiBase").value = "http://127.0.0.1:8000";
  element("apiBase").value = "http://127.0.0.1:8000";
  element("appView").hidden = true;
  element("policyId").value = "default";
  vm.runInContext(demoScript, context, { filename: "demo.html" });

  return {
    context,
    element,
    sessionStorage,
    setFetch(nextFetch) {
      currentFetch = nextFetch;
    },
    run(source) {
      return vm.runInContext(source, context);
    },
  };
}

function abortError() {
  return new DOMException("aborted", "AbortError");
}

function jsonResponse(payload, { status = 200, signal, bodyDelayMs = 0, bodyError } = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text() {
      if (bodyError) return Promise.reject(bodyError);
      return new Promise((resolve, reject) => {
        const timer = setTimeout(() => resolve(payload === null ? "" : JSON.stringify(payload)), bodyDelayMs);
        if (signal) {
          signal.addEventListener("abort", () => {
            clearTimeout(timer);
            reject(abortError());
          }, { once: true });
        }
      });
    },
  };
}

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

test("requestJson keeps timeout active through headers and body parsing", async () => {
  const harness = createHarness();

  harness.setFetch((url, options) => new Promise((resolve, reject) => {
    const timer = setTimeout(() => resolve(jsonResponse({ ok: true }, { signal: options.signal })), 50);
    options.signal.addEventListener("abort", () => {
      clearTimeout(timer);
      reject(abortError());
    }, { once: true });
  }));
  await assert.rejects(
    harness.run("requestJson('/headers-delay', { timeoutMs: 10 })"),
    (error) => error.kind === "timeout",
  );

  harness.setFetch((url, options) => Promise.resolve(
    jsonResponse({ ok: true }, { signal: options.signal, bodyDelayMs: 50 }),
  ));
  await assert.rejects(
    harness.run("requestJson('/body-delay', { timeoutMs: 10 })"),
    (error) => error.kind === "timeout",
  );

  harness.setFetch(() => Promise.resolve(jsonResponse(null, { bodyError: new Error("body failed") })));
  await assert.rejects(
    harness.run("requestJson('/body-failure')"),
    (error) => error.kind === "network",
  );

  harness.setFetch(() => Promise.resolve({ ok: true, status: 200, text: async () => "not-json" }));
  await assert.rejects(
    harness.run("requestJson('/invalid-json')"),
    (error) => error.kind === "invalid-response",
  );

  harness.setFetch(() => Promise.resolve({ ok: true, status: 204, text: async () => "" }));
  const emptyResult = await harness.run("requestJson('/empty')");
  assert.equal(emptyResult.payload, null);
  assert.equal(emptyResult.status, 204);
});

test("requestJson distinguishes caller abort during body consumption", async () => {
  const harness = createHarness();
  harness.setFetch((url, options) => Promise.resolve(
    jsonResponse({ ok: true }, { signal: options.signal, bodyDelayMs: 100 }),
  ));
  const result = harness.run(`(() => {
    const controller = new AbortController();
    const pending = requestJson('/abort-body', { controller, timeoutMs: 1000 });
    window.setTimeout(() => controller.abort(), 5);
    return pending;
  })()`);
  await assert.rejects(result, (error) => error.kind === "aborted");
});

test("signup completion uses the captured mode and locks mutable controls", async () => {
  const response = deferred();
  let requestedUrl = "";
  const harness = createHarness({
    fetchImpl: (url) => {
      requestedUrl = url;
      return response.promise;
    },
  });
  harness.element("authApiBase").value = "http://127.0.0.1:8000";
  harness.element("authEmail").value = "signup@example.com";
  harness.element("authPassword").value = "password123";
  harness.element("confirmPassword").value = "password123";
  await harness.element("signupTab").emit("click");

  const submit = harness.element("authForm").emit("submit");
  assert.equal(harness.element("authEmail").disabled, true);
  assert.equal(harness.element("loginTab").disabled, true);
  await harness.element("loginTab").emit("click");
  response.resolve(jsonResponse({ email: "signup@example.com" }));
  await submit;

  assert.match(requestedUrl, /\/auth\/signup$/);
  assert.equal(harness.sessionStorage.getItem("orca_auth_token"), null);
  assert.match(harness.element("authMessage").textContent, /가입이 완료/);
  assert.equal(harness.element("authEmail").disabled, false);
  assert.equal(harness.element("loginTab").disabled, false);
});

test("login rejects a response without access_token and invalidates delayed navigation", async () => {
  const harness = createHarness({
    fetchImpl: (url, options) => Promise.resolve(jsonResponse({ email: "user@example.com" }, { signal: options.signal })),
  });
  harness.element("authApiBase").value = "http://127.0.0.1:8000";
  harness.element("authEmail").value = "user@example.com";
  harness.element("authPassword").value = "password123";
  await harness.element("authForm").emit("submit");
  assert.equal(harness.sessionStorage.getItem("orca_auth_token"), null);
  assert.match(harness.element("authMessage").textContent, /access_token/);
  assert.equal(harness.element("appView").hidden, true);

  harness.setFetch((url, options) => Promise.resolve(jsonResponse({
    email: "user@example.com",
    access_token: "valid-token",
  }, { signal: options.signal })));
  await harness.element("authForm").emit("submit");
  harness.run("clearStoredAuth('cancel navigation')");
  await new Promise((resolve) => setTimeout(resolve, 400));
  assert.equal(harness.element("appView").hidden, true);
  assert.equal(harness.sessionStorage.getItem("orca_auth_token"), null);
});

async function prepareAdminHarness() {
  const adminResponses = [deferred(), deferred(), deferred()];
  let index = 0;
  const harness = createHarness({
    fetchImpl: (url) => {
      if (url.endsWith("/auth/logout")) return Promise.resolve(jsonResponse(null, { status: 204 }));
      return adminResponses[index++].promise;
    },
  });
  harness.run(`authToken = 'user-token'; authOrigin = 'http://127.0.0.1:8000'; apiBase.value = authOrigin;`);
  harness.element("adminToken").value = "admin-token";
  const refresh = harness.element("refreshAdminBtn").emit("click");
  await new Promise((resolve) => setImmediate(resolve));
  return { adminResponses, harness, refresh };
}

function resolveAdminResponses(adminResponses) {
  adminResponses[0].resolve(jsonResponse({
    total_requests: 99,
    blocked_requests: 3,
    masked_requests: 2,
    warned_requests: 1,
    allowed_requests: 93,
    error_requests: 0,
  }));
  adminResponses[1].resolve(jsonResponse([{ reason_code: "SAFE_INPUT", count: 93 }]));
  adminResponses[2].resolve(jsonResponse([]));
}

test("stale admin responses cannot repopulate data after token change", async () => {
  const { adminResponses, harness, refresh } = await prepareAdminHarness();
  harness.element("adminToken").value = "changed-token";
  await harness.element("adminToken").emit("input");
  resolveAdminResponses(adminResponses);
  await refresh;

  assert.equal(harness.element("totalRequests").textContent, "-");
  assert.equal(harness.run("adminAuthenticated"), false);
  assert.match(harness.element("adminStatus").textContent, /토큰이 변경/);
});

test("stale admin responses cannot repopulate data after logout or origin change", async (t) => {
  await t.test("logout", async () => {
    const { adminResponses, harness, refresh } = await prepareAdminHarness();
    await harness.element("logoutBtn").emit("click");
    resolveAdminResponses(adminResponses);
    await refresh;
    assert.equal(harness.element("totalRequests").textContent, "-");
    assert.equal(harness.run("adminAuthenticated"), false);
  });

  await t.test("origin change", async () => {
    const { adminResponses, harness, refresh } = await prepareAdminHarness();
    harness.element("apiBase").value = "http://127.0.0.1:9000";
    await harness.element("apiBase").emit("input");
    resolveAdminResponses(adminResponses);
    await refresh;
    assert.equal(harness.element("totalRequests").textContent, "-");
    assert.equal(harness.run("adminAuthenticated"), false);
  });

  await t.test("user session change", async () => {
    const { adminResponses, harness, refresh } = await prepareAdminHarness();
    harness.run("authToken = 'different-user-token'");
    resolveAdminResponses(adminResponses);
    await refresh;
    assert.equal(harness.element("totalRequests").textContent, "-");
    assert.equal(harness.run("adminAuthenticated"), false);
  });
});
