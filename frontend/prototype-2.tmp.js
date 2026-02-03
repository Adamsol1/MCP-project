
      const state = {
        theme: "light",
        sidebarCollapsed: false,
        sidebarOpenMobile: false,
        control: {
          aiRounds: 3,
          aiCountries: ["US", "UK"],
          modelPreset: "Balanced",
          modelCount: 2,
          language: "English",
          uploadedFiles: [],
        },
        conversations: [],
        activeConversationId: "",
        uploadPrompted: false,
        run: {
          active: false,
          cancelled: false,
          progress: 0,
          stage: "",
          cancelToken: null,
        },
      };

      const createConversation = () => {
        const id = "convo_" + Date.now().toString(36);
        const convo = {
          id,
          title: "New chat",
          updatedAt: Date.now(),
          messages: [],
        };
        state.conversations.unshift(convo);
        state.activeConversationId = id;
        state.uploadPrompted = false;
        return convo;
      };
      const renameConversation = (id) => {
        const convo = state.conversations.find((c) => c.id === id);
        if (!convo) return;
        const nextTitle = prompt("Rename conversation", convo.title);
        if (!nextTitle) return;
        convo.title = nextTitle.trim().slice(0, 60);
        convo.updatedAt = Date.now();
      };

      const deleteConversation = (id) => {
        const index = state.conversations.findIndex((c) => c.id === id);
        if (index === -1) return;
        const ok = confirm("Delete this conversation?");
        if (!ok) return;
        state.conversations.splice(index, 1);
        if (state.activeConversationId === id) {
          state.activeConversationId = state.conversations[0]?.id || "";
        }
      };

      const addMessage = (convoId, role, content, meta) => {
        const convo = state.conversations.find((c) => c.id === convoId);
        if (!convo) return;
        convo.messages.push({
          id: "msg_" + Date.now().toString(36) + Math.random().toString(36),
          role,
          content,
          createdAt: Date.now(),
          meta: meta || null,
        });
        convo.updatedAt = Date.now();
      };

      const mockGenerateResponse = (userText, control) => {
        const lang = control.language;
        const presets = {
          "Fast (small)": { verbosity: 1, baseDelay: 400 },
          Balanced: { verbosity: 2, baseDelay: 700 },
          "Deep (large)": { verbosity: 3, baseDelay: 1100 },
          Custom: { verbosity: 3, baseDelay: 900 },
        };

        const flavor = presets[control.modelPreset] || presets.Balanced;
        const fileMention = control.uploadedFiles.length
          ? `I parsed ${control.uploadedFiles.length} file(s): ${control.uploadedFiles
              .map((f) => f.name)
              .join(", ")}.`
          : "No files were attached, so I focused on the text.";

        const baseText = {
          English: `Assessment summary (${control.modelPreset}, ${control.modelCount} models).\n${fileMention}`,
          "Norwegian (Bokm�l)": `Oppsummering (${control.modelPreset}, ${control.modelCount} modeller).\n${fileMention}`,
          "Chinese (Simplified)": `Summary (${control.modelPreset}, ${control.modelCount} models).\n${fileMention}`,
        };

        const iocs = [
          { type: "ip", value: "1.2.3.4", severity: "medium" },
          { type: "domain", value: "evil-domain.com", severity: "high" },
          { type: "hash", value: "e3b0c442...", severity: "low" },
        ];

        const citations = [
          { label: "Case note", source: "Internal telemetry" },
          { label: "Threat feed", source: "Mock OSINT" },
        ];

        const steps = [
          { name: "Collection", duration: `${(flavor.baseDelay / 1000).toFixed(1)}s` },
          { name: "Normalize", duration: `${(flavor.baseDelay / 1200).toFixed(1)}s` },
          { name: "Analyze", duration: `${(flavor.baseDelay / 800).toFixed(1)}s` },
          { name: "Review", duration: `${(flavor.baseDelay / 900).toFixed(1)}s` },
        ];

        const responseText =
          baseText[lang] +
          "\n\nExtracted IOCs:\n" +
          iocs.map((ioc) => `- ${ioc.type}: ${ioc.value} (${ioc.severity})`).join("\n") +
          "\n\nRecommended next steps:\n- Enrich indicators\n- Correlate endpoint logs\n- Escalate to IR team";

        return {
          assistantTextMarkdown: responseText,
          extractedIocs: iocs,
          citations,
          runTrace: { steps },
        };
      };

      const streamAssistantMessage = (fullText, onChunk, onDone, cancelToken) => {
        let index = 0;
        const interval = setInterval(() => {
          if (cancelToken.cancelled) {
            clearInterval(interval);
            onDone(true);
            return;
          }
          index += Math.floor(Math.random() * 5) + 2;
          const chunk = fullText.slice(0, index);
          onChunk(chunk);
          if (index >= fullText.length) {
            clearInterval(interval);
            onDone(false);
          }
        }, 45);
      };

      const formatTime = (timestamp) => {
        const date = new Date(timestamp);
        return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      };

      const getActiveConversation = () =>
        state.conversations.find((c) => c.id === state.activeConversationId);

      const ensureActiveConversation = () => {
        if (!state.conversations.length) {
          createConversation();
        }
        if (!state.activeConversationId) {
          state.activeConversationId = state.conversations[0].id;
        }
      };

      const renderMessage = (message) => {
        const safeContent = message.content
          .split("\n")
          .map((line) => `<div>${line}</div>`)
          .join("");

        const copyButton =
          message.role === "assistant"
            ? `<button class="copy-btn" data-action="copy" data-id="${message.id}">Copy</button>`
            : "";

        const runTrace =
          message.meta && message.meta.runTrace
            ? `<details class="run-trace"><summary>Run details</summary>${message.meta.runTrace.steps
                .map(
                  (step) =>
                    `<div class="run-step"><strong>${step.name}</strong> � ${step.duration}</div>`
                )
                .join("")}</details>`
            : "";

        const artifacts =
          message.role === "assistant" && message.meta?.showArtifacts
            ? `<div class="artifacts">
                <span>Report ready</span>
                <button data-action="download-report">Download report</button>
                <button data-action="download-json">Download JSON</button>
              </div>`
            : "";

        return `
          <div class="message ${message.role}">
            <div class="bubble">${safeContent}</div>
            <div class="message-actions">
              <span>${formatTime(message.createdAt)}</span>
              ${copyButton}
            </div>
            ${artifacts}
            ${runTrace}
          </div>
        `;
      };

      const render = () => {
        ensureActiveConversation();
        document.documentElement.setAttribute("data-theme", state.theme);

        const activeConversation = getActiveConversation();
        const query = state.searchQuery || "";
        const filtered = state.conversations.filter((c) =>
          c.title.toLowerCase().includes(query.toLowerCase())
        );

        const app = document.getElementById("app");
        app.innerHTML = `
          <div class="drawer-backdrop ${state.sidebarOpenMobile ? "active" : ""}" data-action="close-drawer"></div>
          <div class="app">
            <aside class="sidebar ${state.sidebarCollapsed ? "collapsed" : ""} ${state.sidebarOpenMobile ? "open" : ""}">
              <div class="sidebar-header">
                <button class="focusable" data-action="toggle-collapse" aria-label="Collapse sidebar">Collapse</button>
                <button class="focusable" data-action="toggle-theme" aria-label="Toggle theme">${
                  state.theme === "light" ? "Dark" : "Light"
                }</button>
              </div>
              <div class="sidebar-body">
                <button class="new-chat focusable" data-action="new-chat">+ New Chat</button>
                <label class="search">
                  Search
                  <input type="text" placeholder="Search" value="${query}" data-action="search" aria-label="Search conversations" />
                </label>
                <div class="conversation-list">
                  ${filtered
                    .map(
                      (convo) => `
                      <div class="conversation-item ${
                        convo.id === state.activeConversationId ? "active" : ""
                      }" data-action="open" data-id="${convo.id}">
                        <div>
                          <div class="conversation-title">${convo.title}</div>
                          <div class="conversation-meta">${new Date(
                            convo.updatedAt
                          ).toLocaleDateString()}</div>
                        </div>
                        <div class="conversation-actions">
                          <button class="icon-only" title="Rename" data-action="rename" data-id="${convo.id}">Rename</button>
                          <button class="icon-only" title="Delete" data-action="delete" data-id="${convo.id}">Delete</button>
                        </div>
                      </div>
                    `
                    )
                    .join("")}
                </div>
              </div>
            </aside>

            <main class="main">
              <div class="topbar">
                <div class="topbar-actions">
                  <button class="sidebar-toggle-mobile" data-action="open-drawer">Menu</button>
                  <div>
                    <div class="title">${activeConversation?.title || "Conversation"}</div>
                    <div class="status">Demo status: mock-only</div>
                  </div>
                </div>
                <div class="topbar-actions">
                  <div class="topbar-language">
                    <label for="top-language-select">Language</label>
                    <select id="top-language-select" data-action="language" aria-label="Language">
                      ${["English", "Norwegian (Bokmal)", "Chinese (Simplified)"]
                        .map(
                          (opt) =>
                            `<option ${
                              state.control.language === opt ? "selected" : ""
                            }>${opt}</option>`
                        )
                        .join("")}
                    </select>
                  </div>
                  <button data-action="clear-chat">Clear</button>
                  <button data-action="toggle-theme">${
                    state.theme === "light" ? "Dark" : "Light"
                  }</button>
                </div>
              </div>
                            <div class="control-bar">
                <div class="control-layout top">
                  <div class="control-section">
                    <h4>Models</h4>
                    <select data-action="model-preset" aria-label="Model preset">
                      ${["Fast (small)", "Balanced", "Deep (large)", "Custom"]
                        .map(
                          (opt) =>
                            `<option ${
                              state.control.modelPreset === opt ? "selected" : ""
                            }>${opt}</option>`
                        )
                        .join("")}
                    </select>
                    <div class="control-row">
                      <span># Models</span>
                      <div class="stepper">
                        <button data-action="model-dec" aria-label="Decrease model count">-</button>
                        <span>${state.control.modelCount}</span>
                        <button data-action="model-inc" aria-label="Increase model count">+</button>
                      </div>
                    </div>
                  </div>

                  <div class="control-section">
                    <h4>AI Counsel</h4>
                    <div class="ai-counsel-inline">
                      <div>
                        <label for="ai-rounds" class="helper-text">Rounds</label>
                        <select id="ai-rounds" data-action="ai-rounds" aria-label="AI counsel rounds">
                          ${[1, 2, 3, 4, 5]
                            .map(
                              (opt) =>
                                `<option ${
                                  state.control.aiRounds === opt ? "selected" : ""
                                }>${opt}</option>`
                            )
                            .join("")}
                        </select>
                      </div>
                      <div>
                        <label for="ai-countries" class="helper-text">Countries to include (comma-separated)</label>
                        <input
                          id="ai-countries"
                          type="text"
                          data-action="ai-countries"
                          value="${state.control.aiCountries.join(", ") }"
                          placeholder="US, UK, Norway"
                          aria-label="AI counsel countries"
                        />
                      </div>
                    </div>
                  </div>
                </div>

                <div class="control-layout bottom">
                  <div class="control-section">
                    <h4>Files</h4>
                    <div class="helper-text">Upload files to enrich the run.</div>
                    <div class="control-row">
                      <button class="focusable" data-action="upload-files">Upload files</button>
                      <button class="focusable" data-action="run-analysis">Run analysis</button>
                      <input type="file" id="file-input" multiple style="display:none" />
                    </div>
                    <div class="chip-list">
                      ${state.control.uploadedFiles
                        .map(
                          (file) => `
                        <span class="chip">${file.name} (${Math.round(file.size / 1024)} KB)
                          <button data-action="remove-file" data-id="${file.id}" aria-label="Remove file">x</button>
                        </span>
                      `
                        )
                        .join("")}
                    </div>
                  </div>

                  <div class="download-group">
                    <button data-action="download-report">Download report</button>
                    <button class="secondary" data-action="download-json">Download JSON</button>
                  </div>
                </div>
              </div>

              <div class="progress-bar ${state.run.active ? "active" : ""}">
                <div class="progress-track">
                  <div class="progress-fill" style="width: ${state.run.progress}%"></div>
                </div>
                <div class="progress-meta">${state.run.stage || ""} ${
                  state.run.progress
                }%</div>
                <button data-action="cancel-run">Cancel</button>
              </div>

              <div class="chat-log" id="chat-log">
                ${activeConversation?.messages.map(renderMessage).join("") || ""}
              </div>

              <button class="jump-latest" data-action="jump">Jump to latest</button>

              <div class="composer">
                <textarea
                  id="composer"
                  rows="1"
                  placeholder="Message Prototype 2..."
                  aria-label="Message input"
                ></textarea>
                <button id="send-btn" ${state.run.active ? "" : "disabled"} data-action="send">${
                  state.run.active ? "Stop" : "Send"
                }</button>
              </div>
            </main>
          </div>
        `;

        const textarea = document.getElementById("composer");
        const sendBtn = document.getElementById("send-btn");
        const chatLog = document.getElementById("chat-log");
        const jumpBtn = document.querySelector(".jump-latest");

        const updateSendState = () => {
          if (!state.run.active) {
            sendBtn.disabled = textarea.value.trim().length === 0;
          }
        };

        const autoGrow = () => {
          textarea.style.height = "auto";
          textarea.style.height = Math.min(textarea.scrollHeight, 160) + "px";
          updateSendState();
        };

        textarea.addEventListener("input", autoGrow);
        autoGrow();

        const handleScroll = () => {
          const nearBottom =
            chatLog.scrollHeight - chatLog.scrollTop - chatLog.clientHeight < 120;
          jumpBtn.style.display = nearBottom ? "none" : "inline-flex";
        };

        chatLog.addEventListener("scroll", handleScroll);
        handleScroll();

        if (!state.preventAutoScroll) {
          chatLog.scrollTop = chatLog.scrollHeight;
        }
      };

      const generateReportText = () => {
        const convo = getActiveConversation();
        const lines = [
          `Conversation: ${convo?.title || ""}`,
          `Language: ${state.control.language}`,
          `Model preset: ${state.control.modelPreset}`,
          `Model count: ${state.control.modelCount}`,
          `Files: ${state.control.uploadedFiles.map((f) => f.name).join(", ")}`,
          "",
          "Messages:",
        ];
        (convo?.messages || []).forEach((m) => {
          lines.push(`[${m.role}] ${m.content}`);
        });
        return lines.join("\n");
      };

      const downloadBlob = (content, filename, type) => {
        const blob = new Blob([content], { type });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
      };

      const downloadReport = () => {
        downloadBlob(generateReportText(), "report.txt", "text/plain");
      };

      const downloadJson = () => {
        const convo = getActiveConversation();
        const payload = {
          meta: {
            generatedAt: new Date().toISOString(),
            conversationId: convo?.id || "",
          },
          settings: {
            modelPreset: state.control.modelPreset,
            modelCount: state.control.modelCount,
            language: state.control.language,
          },
          files: state.control.uploadedFiles,
          messages: convo?.messages || [],
        };
        downloadBlob(JSON.stringify(payload, null, 2), "conversation.json", "application/json");
      };

      const startRun = () => {
        if (state.run.active) return;
        state.run.active = true;
        state.run.cancelled = false;
        state.run.progress = 0;
        state.run.stage = "Collecting...";
        state.run.cancelToken = { cancelled: false };
        render();

        const stages = [
          { label: "Collecting...", until: 25 },
          { label: "Normalizing...", until: 50 },
          { label: "Analyzing...", until: 80 },
          { label: "Reviewing...", until: 100 },
        ];

        let stageIndex = 0;
        const interval = setInterval(() => {
          if (state.run.cancelToken?.cancelled) {
            clearInterval(interval);
            state.run.active = false;
            state.run.stage = "Cancelled";
            state.run.progress = 0;
            render();
            return;
          }
          state.run.progress += Math.floor(Math.random() * 6) + 3;
          if (state.run.progress >= stages[stageIndex].until) {
            stageIndex = Math.min(stageIndex + 1, stages.length - 1);
            state.run.stage = stages[stageIndex].label;
          }
          if (state.run.progress >= 100) {
            state.run.progress = 100;
            state.run.active = false;
            state.run.stage = "Completed";
            clearInterval(interval);
          }
          render();
        }, 220);
      };

      const finishRun = () => {
        state.run.active = false;
        state.run.stage = "Completed";
        state.run.progress = 100;
      };

      const sendMessage = () => {
        const textarea = document.getElementById("composer");
        const text = textarea.value.trim();
        if (!text || state.run.active) return;

        const activeId = state.activeConversationId;
        addMessage(activeId, "user", text);
        textarea.value = "";
        state.preventAutoScroll = false;

        if (!state.uploadPrompted && state.control.uploadedFiles.length === 0) {
          state.uploadPrompted = true;
          const wantsUpload = confirm("Upload a file for this run?");
          if (wantsUpload) {
            const input = document.getElementById("file-input");
            if (input) {
              input.click();
            }
          }
        }

        startRun();

        if (state.control.uploadedFiles.length) {
          addMessage(
            activeId,
            "tool",
            `Parsing ${state.control.uploadedFiles.length} file(s)... extracted ${
              state.control.uploadedFiles.length * 3
            } IOCs.`
          );
        }

        const response = mockGenerateResponse(text, state.control);
        const assistantMessage = {
          id: "msg_" + Date.now().toString(36),
          role: "assistant",
          content: "",
          createdAt: Date.now(),
          meta: { runTrace: response.runTrace, showArtifacts: true },
        };

        const convo = getActiveConversation();
        convo.messages.push(assistantMessage);

        state.run.cancelToken = { cancelled: false };
        render();

        streamAssistantMessage(
          response.assistantTextMarkdown,
          (chunk) => {
            assistantMessage.content = chunk;
            const chatLog = document.getElementById("chat-log");
            const nearBottom =
              chatLog.scrollHeight - chatLog.scrollTop - chatLog.clientHeight < 140;
            state.preventAutoScroll = !nearBottom;
            render();
          },
          (cancelled) => {
            if (cancelled) {
              assistantMessage.content += "\n\n[Response cancelled]";
            }
            finishRun();
            render();
          },
          state.run.cancelToken
        );
      };

      const runAnalysis = () => {
        if (state.run.active) return;
        startRun();
        const response = mockGenerateResponse("(analysis)", state.control);
        const activeId = state.activeConversationId;
        const assistantMessage = {
          id: "msg_" + Date.now().toString(36),
          role: "assistant",
          content: "",
          createdAt: Date.now(),
          meta: { runTrace: response.runTrace, showArtifacts: true },
        };
        const convo = getActiveConversation();
        convo.messages.push(assistantMessage);

        streamAssistantMessage(
          response.assistantTextMarkdown,
          (chunk) => {
            assistantMessage.content = chunk;
            render();
          },
          () => {
            finishRun();
            render();
          },
          state.run.cancelToken || { cancelled: false }
        );
      };

      const clearChat = () => {
        const convo = getActiveConversation();
        if (!convo) return;
        const ok = confirm("Clear this chat?");
        if (!ok) return;
        convo.messages = [];
        convo.updatedAt = Date.now();
        state.uploadPrompted = false;
        render();
      };

      const handleClick = (event) => {
        const actionEl = event.target.closest("[data-action]");
        if (!actionEl) return;
        const action = actionEl.dataset.action;
        const id = actionEl.dataset.id;

        if (action === "toggle-collapse") {
          state.sidebarCollapsed = !state.sidebarCollapsed;
          render();
          return;
        }

        if (action === "toggle-theme") {
          state.theme = state.theme === "light" ? "dark" : "light";
          render();
          return;
        }

        if (action === "new-chat") {
          createConversation();
          render();
          return;
        }

        if (action === "open" && id) {
          state.activeConversationId = id;
          state.sidebarOpenMobile = false;
          render();
          return;
        }

        if (action === "rename" && id) {
          renameConversation(id);
          render();
          return;
        }

        if (action === "delete" && id) {
          deleteConversation(id);
          render();
          return;
        }

        if (action === "send") {
          if (state.run.active) {
            if (state.run.cancelToken) {
              state.run.cancelToken.cancelled = true;
            }
          } else {
            sendMessage();
          }
          return;
        }

        if (action === "copy" && id) {
          const convo = getActiveConversation();
          const msg = convo?.messages.find((m) => m.id === id);
          if (msg) {
            navigator.clipboard.writeText(msg.content || "");
          }
          return;
        }

        if (action === "clear-chat") {
          clearChat();
          return;
        }

        if (action === "open-drawer") {
          state.sidebarOpenMobile = true;
          render();
          return;
        }

        if (action === "close-drawer") {
          state.sidebarOpenMobile = false;
          render();
          return;
        }

        if (action === "jump") {
          const chatLog = document.getElementById("chat-log");
          chatLog.scrollTop = chatLog.scrollHeight;
          return;
        }

        if (action === "upload-files") {
          document.getElementById("file-input").click();
          return;
        }

        if (action === "remove-file" && id) {
          state.control.uploadedFiles = state.control.uploadedFiles.filter(
            (f) => f.id !== id
          );
          render();
          return;
        }

        if (action === "model-dec") {
          state.control.modelCount = Math.max(1, state.control.modelCount - 1);
          render();
          return;
        }

        if (action === "model-inc") {
          state.control.modelCount = Math.min(5, state.control.modelCount + 1);
          render();
          return;
        }

        if (action === "download-report") {
          downloadReport();
          return;
        }

        if (action === "download-json") {
          downloadJson();
          return;
        }

        if (action === "run-analysis") {
          runAnalysis();
          return;
        }

        if (action === "cancel-run") {
          if (state.run.cancelToken) {
            state.run.cancelToken.cancelled = true;
          }
          return;
        }
      };

      const handleInput = (event) => {
        if (event.target.matches("[data-action='ai-rounds']")) {
          state.control.aiRounds = Number(event.target.value);
          render();
          return;
        }

        if (event.target.matches("[data-action='ai-countries']")) {
          state.control.aiCountries = event.target.value
            .split(",")
            .map((c) => c.trim())
            .filter((c) => c.length);
          return;
        }


        if (event.target.matches("[data-action='search']")) {
          state.searchQuery = event.target.value;
          render();
          return;
        }


        if (event.target.matches("[data-action='model-preset']")) {
          state.control.modelPreset = event.target.value;
          render();
          return;
        }

        if (event.target.matches("[data-action='language']")) {
          state.control.language = event.target.value;
          render();
          return;
        }
      };

      const handleKeydown = (event) => {
        const textarea = event.target.closest("#composer");
        if (!textarea) return;
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          sendMessage();
        }
      };

      const handleFileChange = (event) => {
        const files = Array.from(event.target.files || []);
        const mapped = files.map((file) => ({
          id: "file_" + Date.now().toString(36) + Math.random().toString(36),
          name: file.name,
          size: file.size,
          lastModified: file.lastModified,
        }));
        state.control.uploadedFiles = state.control.uploadedFiles.concat(mapped);
        event.target.value = "";
        render();
      };
      ensureActiveConversation();
      if (!state.conversations.length) {
        const convo = createConversation();
        addMessage(
          convo.id,
          "assistant",
          "Welcome to Prototype 2. Use the control bar to configure your mock threat-intel run."
        );
      }

      document.addEventListener("click", handleClick);
      document.addEventListener("input", handleInput);
      document.addEventListener("keydown", handleKeydown);
      document.addEventListener("change", (event) => {
        if (event.target.id === "file-input") {
          handleFileChange(event);
        }
      });

      render();
    