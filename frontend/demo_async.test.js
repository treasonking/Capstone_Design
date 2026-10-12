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

  insertBefore(child) { this.children.push(child); }

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

function createHarness({ storage = {}, fetchImpl, requestTimeoutMs, route = "/login" } = {}) {
  const elements = new Map();
  const element = (id) => {
    if (!elements.has(id)) elements.set(id, new FakeElement(id));
    return elements.get(id);
  };
  const sessionStorage = new FakeStorage(storage);
  let currentFetch = fetchImpl || (() => Promise.reject(new Error("unexpected fetch")));
  const location = { pathname: route };
  const windowEvents = new FakeElement();
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
      location,
      history: {
        pushState: (state, title, path) => { location.pathname = path; },
        replaceState: (state, title, path) => { location.pathname = path; },
      },
      addEventListener: (type, callback) => windowEvents.addEventListener(type, callback),
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
    windowEvents,
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

function chatHarness(options = {}) {
  const h = createHarness(options);
  h.run("authToken = 'user-token'; authOrigin = 'http://127.0.0.1:8000'; setRoute('/app'); showApp('synthetic@example.com');");
  return h;
}

function chatFetch(final = { action: "ALLOW", content: "safe answer" }, analysis = "ALLOW", requests = []) {
  return (url, options) => {
    requests.push({ url, body: JSON.parse(options.body), headers: options.headers });
    return Promise.resolve(jsonResponse(url.endsWith("/proxy/analyze") ? { action: analysis } : final, { signal: options.signal }));
  };
}

test("CHAT final content only, memory-only history, no policy or history sent, literal HTML", async () => {
  const requests = [];
  const raw = '<img src=x onerror="alert(1)">';
  const h = chatHarness({ fetchImpl: chatFetch({ action: "ALLOW", content: raw }, "ALLOW", requests) });
  h.element("chatInput").value = raw;
  await h.element("chatForm").emit("submit");
  assert.equal(h.run("chatTurns[0].answer.textContent"), raw);
  assert.equal(h.run("chatTurns[0].answer.hidden"), false);
  h.element("chatInput").value = "second question";
  await h.element("chatForm").emit("submit");
  assert.equal(h.run("chatTurns.length"), 2);
  assert.deepEqual(requests.map(r => r.body), [{message:raw}, {message:raw}, {message:"second question"}, {message:"second question"}]);
  assert.ok(requests.every(r => !r.headers["X-Admin-Token"]));
  assert.equal(h.sessionStorage.values.size, 0);
  assert.equal(h.element("userConsole").hidden, true);
});

test("CHAT empty input, IME Enter, Shift Enter and duplicate submission guards", async () => {
  const response = deferred();
  let calls = 0;
  const h = chatHarness({ fetchImpl: () => { calls++; return response.promise; } });
  await h.element("chatForm").emit("submit");
  assert.equal(calls, 0);
  h.element("chatInput").value = "한글 질문";
  for (const event of [{isComposing:true}, {keyCode:229}, {shiftKey:true}]) {
    await h.element("chatInput").emit("keydown", {key:"Enter", ...event});
  }
  assert.equal(calls, 0);
  const pending = h.element("chatInput").emit("keydown", {key:"Enter"});
  await h.element("chatForm").emit("submit");
  assert.equal(calls, 1);
  response.resolve(jsonResponse({action:"BLOCK"}));
  await pending;
  assert.equal(h.run("chatTurns.length"), 1);
  assert.equal(h.element("chatSendBtn").disabled, false);
});

test("CHAT MASK notice and BLOCK never render unsafe content", async () => {
  const h = chatHarness({ fetchImpl: chatFetch({action:"MASK", content:"masked answer", input_masked:true}) });
  h.element("chatInput").value = "synthetic contact";
  await h.element("chatForm").emit("submit");
  assert.match(h.run("chatTurns[0].status.textContent"), /가리고 전송/);
  h.setFetch(chatFetch({action:"BLOCK", content:"must never appear"}));
  h.element("chatInput").value = "question";
  await h.element("chatForm").emit("submit");
  assert.equal(h.run("chatTurns[1].answer.hidden"), true);
  assert.equal(h.run("chatTurns[1].answer.textContent"), "");
});

test("CHAT WARN cancel has no provider request; confirm uses original snapshot", async () => {
  const requests = [];
  const h = chatHarness({fetchImpl:chatFetch({action:"WARN", content:"safe final"}, "WARN", requests)});
  h.run("window.confirm = () => false");
  h.element("chatInput").value = "warn question";
  await h.element("chatForm").emit("submit");
  assert.equal(requests.length, 1);
  assert.equal(h.element("chatInput").value, "warn question");
  h.run("window.confirm = () => { chatInput.value = 'mutated'; return true; }");
  await h.element("chatForm").emit("submit");
  assert.equal(requests[2].body.message, "warn question");
  assert.equal(h.run("chatTurns[1].answer.textContent"), "safe final");
});

test("CHAT errors and body timeout recover with manual original-input retry only", async (t) => {
  for (const failure of ["server", "provider", "body-timeout"]) {
    await t.test(failure, async () => {
      let calls = 0;
      const h = chatHarness({requestTimeoutMs:10, fetchImpl:(url, options) => {
        calls++;
        if (url.endsWith("/proxy/analyze")) return Promise.resolve(jsonResponse({action:"ALLOW"}));
        if (failure === "provider") return Promise.resolve(jsonResponse({action:"ERROR", content:"internal secret"}));
        return Promise.resolve(jsonResponse({detail:"internal secret", action:"ALLOW", content:"late"}, {
          status:failure === "server" ? 500 : 200, signal:options.signal, bodyDelayMs:failure === "body-timeout" ? 80 : 0,
        }));
      }});
      h.element("chatInput").value = "original question";
      await h.element("chatForm").emit("submit");
      assert.equal(calls, 2);
      assert.equal(h.run("chatTurns[0].answer.hidden"), true);
      assert.equal(h.run("chatTurns[0].retry.hidden"), false);
      assert.doesNotMatch(h.run("chatTurns[0].status.textContent"), /internal secret/);
      assert.equal(h.element("chatSendBtn").disabled, false);
      assert.equal(h.element("chatInput").disabled, false);
      const requests = [];
      h.setFetch(chatFetch(undefined, "ALLOW", requests));
      h.element("chatInput").value = "different draft";
      await h.run("chatTurns[0].retry.emit('click')");
      assert.equal(requests[1].body.message, "original question");
      assert.equal(h.run("chatTurns.length"), 1);
      assert.equal(h.run("chatTurns[0].answer.textContent"), "safe answer");
      assert.equal(h.element("chatInput").value, "different draft");
    });
  }
});

test("CHAT invalidation prevents stale response or finally after new chat, route leave, logout", async (t) => {
  for (const kind of ["new", "route", "logout", "pagehide"]) {
    await t.test(kind, async () => {
      const old = deferred();
      const h = chatHarness({fetchImpl:(url) => url.endsWith("/proxy/chat") ? old.promise : Promise.resolve(jsonResponse({action:"ALLOW"}))});
      h.element("chatInput").value = "old question";
      const pending = h.element("chatForm").emit("submit");
      await new Promise(r => setTimeout(r, 5));
      if (kind === "new") await h.element("newChatBtn").emit("click");
      if (kind === "route") h.run("navigateTo('/login')");
      if (kind === "logout") await h.element("logoutBtn").emit("click");
      if (kind === "pagehide") await h.windowEvents.emit("pagehide");
      assert.equal(h.run("chatTurns.length"), 0);
      h.run("authToken='new-token'; authOrigin='http://127.0.0.1:8000'; setRoute('/app');");
      h.setFetch(chatFetch());
      h.element("chatInput").value = "new question";
      await h.element("chatForm").emit("submit");
      old.resolve(jsonResponse({action:"ALLOW", content:"stale"}));
      await pending;
      assert.equal(h.run("chatTurns.length"), 1);
      assert.equal(h.run("chatTurns[0].answer.textContent"), "safe answer");
      assert.equal(h.element("chatSendBtn").disabled, false);
    });
  }
});

test("RESTORE 401 clears token; origin change never sends old bearer to new API", async () => {
  let calls = 0;
  const storage = {orca_auth_token:"stored", orca_auth_origin:"http://127.0.0.1:8000"};
  const h = createHarness({storage, fetchImpl:() => Promise.resolve(jsonResponse({}, {status:401}))});
  await new Promise(r => setTimeout(r, 10));
  assert.equal(h.sessionStorage.getItem("orca_auth_token"), null);
  const other = createHarness({storage:{...storage, orca_auth_origin:"http://127.0.0.1:9000"}, fetchImpl:() => {calls++;}});
  assert.equal(calls, 0);
  assert.equal(other.sessionStorage.getItem("orca_auth_token"), null);
});

test("stale proxy 401 cannot log out a newer user session", async () => {
  const response = deferred();
  const h = chatHarness({fetchImpl:() => response.promise});
  h.element("chatInput").value = "old question";
  const pending = h.element("chatForm").emit("submit");
  h.run("resetChat(); authToken='new-session';");
  response.resolve(jsonResponse({}, {status:401}));
  await pending;
  assert.equal(h.run("authToken"), "new-session");
  assert.equal(h.run("chatTurns.length"), 0);
});

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
  const adminResponses = [deferred(), deferred(), deferred(), deferred()];
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
  adminResponses[3].resolve(jsonResponse({ provider: "mock" }));
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
  const oldResponses = [deferred(), deferred(), deferred(), deferred()];
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
