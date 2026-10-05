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

function createHarness({ storage = {}, fetchImpl, requestTimeoutMs } = {}) {
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
  const executableScript = requestTimeoutMs === undefined
    ? demoScript
    : demoScript.replace(
      "const REQUEST_TIMEOUT_MS = 15000;",
      `const REQUEST_TIMEOUT_MS = ${requestTimeoutMs};`,
    );
  if (requestTimeoutMs !== undefined) {
    assert.notEqual(executableScript, demoScript, "test timeout override must match the product constant");
  }
  vm.runInContext(executableScript, context, { filename: "demo.html" });

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

function abortableJsonFetch(payload, { delayMs = 50, status = 200 } = {}) {
  return (url, options) => new Promise((resolve, reject) => {
    const timer = setTimeout(
      () => resolve(jsonResponse(typeof payload === "function" ? payload(url) : payload, { status })),
      delayMs,
    );
    options.signal.addEventListener("abort", () => {
      clearTimeout(timer);
      reject(abortError());
    }, { once: true });
  });
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

test("AUTH-TIMEOUT restores login controls and permits a successful retry", async () => {
  const harness = createHarness({
    requestTimeoutMs: 10,
    fetchImpl: abortableJsonFetch({ access_token: "too-late" }),
  });
  harness.element("authEmail").value = "user@example.com";
  harness.element("authPassword").value = "password123";

  await harness.element("authForm").emit("submit");

  assert.match(harness.element("authMessage").textContent, /시간이 초과/);
  assert.equal(harness.run("authBusy"), false);
  for (const id of ["authApiBase", "authEmail", "authPassword", "confirmPassword", "authSubmit", "loginTab", "signupTab"]) {
    assert.equal(harness.element(id).disabled, false, `${id} should be enabled after timeout`);
  }
  assert.equal(harness.element("authSubmit").classList.values.has("is-loading"), false);
  assert.equal(harness.element("authSubmit").textContent, "로그인");
  assert.equal(harness.sessionStorage.getItem("orca_auth_token"), null);

  harness.setFetch((url, options) => Promise.resolve(jsonResponse({
    email: "user@example.com",
    access_token: "retry-token",
  }, { signal: options.signal })));
  await harness.element("authForm").emit("submit");
  assert.equal(harness.sessionStorage.getItem("orca_auth_token"), "retry-token");
});

test("SIGNUP-TIMEOUT restores signup controls and keeps conflict-to-login recovery usable", async () => {
  const harness = createHarness({
    requestTimeoutMs: 10,
    fetchImpl: abortableJsonFetch({ email: "signup@example.com" }),
  });
  harness.element("authEmail").value = "signup@example.com";
  harness.element("authPassword").value = "password123";
  harness.element("confirmPassword").value = "password123";
  await harness.element("signupTab").emit("click");

  await harness.element("authForm").emit("submit");

  assert.match(harness.element("authMessage").textContent, /시간이 초과/);
  assert.equal(harness.run("authBusy"), false);
  assert.equal(harness.element("confirmPassword").disabled, false);
  assert.equal(harness.element("loginTab").disabled, false);
  assert.equal(harness.element("authSubmit").textContent, "회원가입");

  harness.setFetch((url, options) => Promise.resolve(jsonResponse(
    { detail: "이미 가입된 이메일입니다. 로그인해 주세요." },
    { status: 409, signal: options.signal },
  )));
  await harness.element("authForm").emit("submit");
  assert.match(harness.element("authMessage").textContent, /이미 가입된 이메일/);
  await harness.element("loginTab").emit("click");
  harness.setFetch((url, options) => Promise.resolve(jsonResponse({
    email: "signup@example.com",
    access_token: "signup-recovery-token",
  }, { signal: options.signal })));
  await harness.element("authForm").emit("submit");
  assert.equal(harness.sessionStorage.getItem("orca_auth_token"), "signup-recovery-token");
});

test("RESTORE-TIMEOUT keeps the stored token and allows a later session restore", async () => {
  const harness = createHarness({
    requestTimeoutMs: 10,
    storage: {
      orca_auth_token: "stored-token",
      orca_auth_origin: "http://127.0.0.1:8000",
    },
    fetchImpl: abortableJsonFetch({ email: "stored@example.com" }),
  });

  await new Promise((resolve) => setTimeout(resolve, 30));
  assert.equal(harness.sessionStorage.getItem("orca_auth_token"), "stored-token");
  assert.match(harness.element("authMessage").textContent, /세션을 확인할 수 없습니다/);
  assert.equal(harness.run("activeAuthController"), null);
  assert.equal(harness.element("appView").hidden, true);

  harness.setFetch((url, options) => Promise.resolve(
    jsonResponse({ email: "stored@example.com" }, { signal: options.signal }),
  ));
  await harness.run("restoreSession()");
  assert.equal(harness.sessionStorage.getItem("orca_auth_token"), "stored-token");
  assert.equal(harness.element("appView").hidden, false);
});

test("AUTH-STALE prevents an invalidated request from overwriting a newer login", async () => {
  const oldResponse = deferred();
  const harness = createHarness({ fetchImpl: () => oldResponse.promise });
  harness.element("authEmail").value = "old@example.com";
  harness.element("authPassword").value = "password123";
  const oldSubmit = harness.element("authForm").emit("submit");
  await new Promise((resolve) => setImmediate(resolve));

  harness.run("invalidateAuthFlow()");
  harness.element("authEmail").value = "new@example.com";
  harness.setFetch((url, options) => Promise.resolve(jsonResponse({
    email: "new@example.com",
    access_token: "new-token",
  }, { signal: options.signal })));
  const newSubmit = harness.element("authForm").emit("submit");
  await newSubmit;
  oldResponse.resolve(jsonResponse({ email: "old@example.com", access_token: "old-token" }));
  await oldSubmit;

  assert.equal(harness.sessionStorage.getItem("orca_auth_token"), "new-token");
  assert.equal(harness.run("authToken"), "new-token");
  assert.equal(harness.run("authBusy"), false);
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

function successfulAdminFetch(total = 99) {
  return (url, options) => {
    if (url.endsWith("/admin/stats")) {
      return Promise.resolve(jsonResponse({
        total_requests: total,
        blocked_requests: 3,
        masked_requests: 2,
        warned_requests: 1,
        allowed_requests: Math.max(total - 6, 0),
        error_requests: 0,
      }, { signal: options.signal }));
    }
    if (url.endsWith("/admin/reason-codes")) {
      return Promise.resolve(jsonResponse([{ reason_code: "SAFE_INPUT", count: total }], { signal: options.signal }));
    }
    return Promise.resolve(jsonResponse([], { signal: options.signal }));
  };
}

test("ADMIN-TIMEOUT clears stale metrics, restores refresh, and permits retry", async () => {
  const harness = createHarness({
    requestTimeoutMs: 10,
    fetchImpl: (url, options) => {
      if (url.endsWith("/admin/stats")) return abortableJsonFetch({ total_requests: 100 })(url, options);
      return Promise.resolve(jsonResponse([], { signal: options.signal }));
    },
  });
  harness.run("authToken = 'user-token'; authOrigin = 'http://127.0.0.1:8000'; apiBase.value = authOrigin;");
  harness.element("adminToken").value = "admin-token";

  await harness.element("refreshAdminBtn").emit("click");

  assert.equal(harness.element("totalRequests").textContent, "-");
  assert.match(harness.element("adminStatus").textContent, /시간이 초과/);
  assert.equal(harness.element("refreshAdminBtn").disabled, false);
  assert.equal(harness.element("adminToken").value, "admin-token");
  assert.equal(harness.run("activeAdminController"), null);

  harness.setFetch(successfulAdminFetch(7));
  await harness.element("refreshAdminBtn").emit("click");
  assert.equal(harness.element("totalRequests").textContent, "7");
  assert.equal(harness.run("adminAuthenticated"), true);
  assert.equal(harness.element("refreshAdminBtn").disabled, false);
});

test("ADMIN-STALE prevents an invalidated refresh from changing newer results or controls", async () => {
  const oldResponses = [deferred(), deferred(), deferred()];
  let oldIndex = 0;
  const harness = createHarness({ fetchImpl: () => oldResponses[oldIndex++].promise });
  harness.run("authToken = 'user-token'; authOrigin = 'http://127.0.0.1:8000'; apiBase.value = authOrigin;");
  harness.element("adminToken").value = "old-admin-token";
  const oldRefresh = harness.element("refreshAdminBtn").emit("click");
  await new Promise((resolve) => setImmediate(resolve));

  harness.element("adminToken").value = "new-admin-token";
  await harness.element("adminToken").emit("input");
  harness.setFetch(successfulAdminFetch(7));
  const newRefresh = harness.element("refreshAdminBtn").emit("click");
  await newRefresh;
  resolveAdminResponses(oldResponses);
  await oldRefresh;

  assert.equal(harness.element("totalRequests").textContent, "7");
  assert.equal(harness.run("adminAuthenticated"), true);
  assert.equal(harness.run("activeAdminController"), null);
  assert.equal(harness.element("refreshAdminBtn").disabled, false);
});

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
