(function () {
  const root = document.querySelector("[data-collect-app]");

  if (!root) {
    return;
  }

  const lang = root.getAttribute("data-lang") || "en";
  const TEXT = {
    en: {
      idle: "Waiting for a local API check.",
      checking: "Checking local API status...",
      ready: "Local collect API is available.",
      offline:
        "Local collect API is not reachable. Start it with `python3 -m src.collect serve` and reopen this page from localhost.",
      running: "Running...",
      success: "Completed successfully.",
      failed: "Request failed.",
      formIdle: "Ready to run.",
      logPlaceholder: "# Command output will appear here.\n",
      terminalStart: "== Job started ==",
      terminalSuccess: "== Job finished successfully ==",
      terminalFailure: "== Job finished with errors ==",
      terminalResult: "== Result ==",
      unexpectedClose: "The log stream closed before a completion event was received.",
      networkError:
        "Could not reach the local API. Make sure the docs site is opened through `python3 -m src.collect serve`.",
    },
    zh: {
      idle: "等待检测本地 API 状态。",
      checking: "正在检测本地 API 状态...",
      ready: "本地采集 API 已可用。",
      offline:
        "当前无法连接本地采集 API。请先运行 `python3 -m src.collect serve`，再通过 localhost 打开本页。",
      running: "正在执行...",
      success: "执行成功。",
      failed: "请求失败。",
      formIdle: "准备执行。",
      logPlaceholder: "# 这里会显示实时执行输出。\n",
      terminalStart: "== 任务开始 ==",
      terminalSuccess: "== 任务执行完成 ==",
      terminalFailure: "== 任务执行失败 ==",
      terminalResult: "== 返回结果 ==",
      unexpectedClose: "日志流已提前关闭，未收到明确的结束事件。",
      networkError:
        "无法连接本地 API。请确认当前页面是通过 `python3 -m src.collect serve` 打开的。",
    },
  };

  const t = TEXT[lang] || TEXT.en;
  const statusNode = root.querySelector("[data-api-status]");
  const outputNode = root.querySelector("[data-api-output]");
  const apiOutputToggle = root.querySelector("[data-api-output-toggle]");
  const forms = root.querySelectorAll("[data-api-form]");
  const checkButton = root.querySelector("[data-api-check]");

  function setStatus(node, message, state) {
    if (!node) {
      return;
    }
    node.textContent = message;
    node.dataset.state = state || "idle";
  }

  function setOutput(node, payload) {
    if (!node) {
      return;
    }
    node.textContent = typeof payload === "string" ? payload : JSON.stringify(payload, null, 2);
  }

  function appendOutput(node, text) {
    if (!node) {
      return;
    }
    const pre = node.closest("pre");
    const shouldStick =
      !pre || pre.scrollTop + pre.clientHeight >= pre.scrollHeight - 24;
    node.textContent += text.endsWith("\n") ? text : `${text}\n`;
    if (pre && shouldStick) {
      pre.scrollTop = pre.scrollHeight;
    }
  }

  function getFormNodes(form) {
    return {
      status: form.querySelector("[data-form-status]"),
      output: form.querySelector("[data-form-output]"),
      outputToggle: form.querySelector("[data-form-output-toggle]"),
    };
  }

  async function request(path, payload) {
    const response = await fetch(path, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload || {}),
    });

    const text = await response.text();
    let data = {};
    try {
      data = text ? JSON.parse(text) : {};
    } catch (_error) {
      data = { ok: false, error: text };
    }

    if (!response.ok || data.ok === false) {
      const error = new Error(data.error || t.failed);
      error.payload = data;
      throw error;
    }

    return data;
  }

  async function requestStream(path, payload, onEvent) {
    const response = await fetch(path, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload || {}),
    });

    if (!response.ok) {
      const text = await response.text();
      let data = {};
      try {
        data = text ? JSON.parse(text) : {};
      } catch (_error) {
        data = { ok: false, error: text };
      }
      const error = new Error(data.error || t.failed);
      error.payload = data;
      throw error;
    }

    if (!response.body) {
      throw new Error(t.networkError);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

      let newlineIndex = buffer.indexOf("\n");
      while (newlineIndex >= 0) {
        const line = buffer.slice(0, newlineIndex).trim();
        buffer = buffer.slice(newlineIndex + 1);
        if (line) {
          onEvent(JSON.parse(line));
        }
        newlineIndex = buffer.indexOf("\n");
      }

      if (done) {
        break;
      }
    }

    const trailing = buffer.trim();
    if (trailing) {
      onEvent(JSON.parse(trailing));
    }
  }

  function collectFormData(form) {
    const result = {};
    const fields = form.querySelectorAll("input, select, textarea");

    for (const field of fields) {
      if (!field.name) {
        continue;
      }
      if (field.type === "checkbox") {
        result[field.name] = field.checked;
        continue;
      }
      const value = field.value.trim();
      if (value === "") {
        continue;
      }
      if (field.dataset.type === "number") {
        result[field.name] = Number(value);
        continue;
      }
      result[field.name] = value;
    }

    return normalizeAccountPayload(result);
  }

  function sanitizeIdentifier(value, options) {
    const settings = options || {};
    const raw = String(value || "")
      .replace(/[\u200B-\u200D\u2060\uFEFF]/g, "")
      .trim();

    if (!raw) {
      return "";
    }
    if (settings.stripAt) {
      return raw.replace(/^@+/, "");
    }
    return raw;
  }

  function normalizeAccountPayload(payload) {
    const result = { ...payload };

    if ((result.platform || "instagram").toLowerCase() !== "instagram") {
      return result;
    }

    const username = sanitizeIdentifier(result.username, { stripAt: true });
    let userId = sanitizeIdentifier(result.user_id);

    if (username) {
      result.username = username;
    } else {
      delete result.username;
    }

    if (!username && userId) {
      const usernameCandidate = userId.replace(/^@+/, "");
      if (usernameCandidate && /\D/.test(usernameCandidate)) {
        result.username = usernameCandidate;
        delete result.user_id;
        return result;
      }
    }

    if (userId) {
      result.user_id = userId;
    } else {
      delete result.user_id;
    }

    return result;
  }

  async function checkHealth() {
    setStatus(statusNode, t.checking, "loading");
    try {
      const response = await fetch("/api/health", { cache: "no-store" });
      if (!response.ok) {
        throw new Error(t.offline);
      }
      const payload = await response.json();
      setStatus(statusNode, t.ready, "ready");
      setOutput(outputNode, payload);
    } catch (_error) {
      setStatus(statusNode, t.offline, "error");
    }
  }

  async function runForm(form) {
    const endpoint = form.getAttribute("data-api-form");
    if (!endpoint) {
      return;
    }

    const submitter = form.querySelector('button[type="submit"]');
    if (submitter) {
      submitter.disabled = true;
      submitter.dataset.originalLabel = submitter.textContent;
      submitter.textContent = t.running;
    }

    const nodes = getFormNodes(form);
    setStatus(nodes.status, t.running, "loading");
    try {
      const payload = collectFormData(form);
      setOutput(nodes.output, t.logPlaceholder);

      if (endpoint === "/api/collect-account") {
        let completed = false;
        appendOutput(nodes.output, t.terminalStart);
        await requestStream(`${endpoint}/stream`, payload, function (event) {
          if (event.event === "log") {
            appendOutput(nodes.output, event.message);
            return;
          }
          if (event.event === "result") {
            appendOutput(nodes.output, "");
            appendOutput(nodes.output, t.terminalResult);
            appendOutput(nodes.output, JSON.stringify(event.data, null, 2));
            return;
          }
          if (event.event === "error") {
            appendOutput(nodes.output, "");
            appendOutput(nodes.output, JSON.stringify(event.data, null, 2));
            return;
          }
          if (event.event === "complete") {
            completed = true;
            appendOutput(nodes.output, "");
            appendOutput(nodes.output, event.ok ? t.terminalSuccess : t.terminalFailure);
            if (!event.ok && nodes.outputToggle) {
              nodes.outputToggle.open = true;
            }
            setStatus(
              nodes.status,
              event.ok ? t.success : event.message || t.failed,
              event.ok ? "ready" : "error"
            );
          }
        });

        if (!completed) {
          throw new Error(t.unexpectedClose);
        }
        return;
      }

      const response = await request(endpoint, payload);
      setStatus(nodes.status, t.success, "ready");
      setOutput(nodes.output, response);
    } catch (error) {
      if (nodes.outputToggle) {
        nodes.outputToggle.open = true;
      }
      setStatus(nodes.status, error.message || t.networkError, "error");
      setOutput(nodes.output, error.payload || { ok: false, error: error.message || t.networkError });
    } finally {
      if (submitter) {
        submitter.disabled = false;
        submitter.textContent = submitter.dataset.originalLabel || submitter.textContent;
      }
    }
  }

  if (checkButton) {
    checkButton.addEventListener("click", function () {
      void request("/api/check", {})
        .then(function (response) {
          setStatus(statusNode, t.success, "ready");
          setOutput(outputNode, response);
        })
        .catch(function (error) {
          if (apiOutputToggle) {
            apiOutputToggle.open = true;
          }
          setStatus(statusNode, error.message || t.failed, "error");
          setOutput(outputNode, error.payload || { ok: false, error: error.message || t.failed });
        });
    });
  }

  for (const form of forms) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      void runForm(form);
    });
  }

  for (const form of forms) {
    const nodes = getFormNodes(form);
    if (nodes.outputToggle) {
      nodes.outputToggle.open = false;
    }
    setStatus(nodes.status, t.formIdle, "idle");
    setOutput(nodes.output, t.logPlaceholder);
  }

  if (apiOutputToggle) {
    apiOutputToggle.open = false;
  }
  setStatus(statusNode, t.idle, "idle");
  void checkHealth();
})();
