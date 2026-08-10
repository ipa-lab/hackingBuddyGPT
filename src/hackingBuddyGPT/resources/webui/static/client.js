/* jshint esversion: 9, browser: true */
/* global console */

(function () {
  "use strict";

  function debounce(func, wait = 100, immediate = false) {
    let timeout;
    return function () {
      const context = this,
        args = arguments;
      const later = function () {
        timeout = null;
        if (!immediate) {
          func.apply(context, args);
        }
      };
      const callNow = immediate && !timeout;
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
      if (callNow) {
        func.apply(context, args);
      }
    };
  }

  function isScrollAtBottom() {
    const content = document.getElementById("main-body");
    console.log("scroll check", content.scrollHeight, content.scrollTop, content.clientHeight);
    return content.scrollHeight - content.scrollTop <= content.clientHeight + 30;
  }

  function scrollUpdate(wasAtBottom) {
    const content = document.getElementById("main-body");
    if (wasAtBottom) {
      console.log("scrolling to bottom");
      content.scrollTop = content.scrollHeight;
    }
  }

  const sidebar = document.getElementById("sidebar");
  const menuToggles = document.getElementsByClassName("menu-toggle");
  Array.from(menuToggles).forEach((menuToggle) => {
    menuToggle.addEventListener("click", () => {
      sidebar.classList.toggle("active");
    });
  });

  let ws = null;
  let currentRun = null;

  const followNewRunsCheckbox = document.getElementById("follow_new_runs");
  let followNewRuns = !window.location.hash && localStorage.getItem("followNewRuns") === "true";
  followNewRunsCheckbox.checked = followNewRuns;

  followNewRunsCheckbox.addEventListener("change", () => {
    followNewRuns = followNewRunsCheckbox.checked;
    localStorage.setItem("followNewRuns", followNewRuns);
  });

  let send = function (type, data) {
    const message = { type: type, data: data };
    console.log("> sending  ", message);
    ws.send(JSON.stringify(message));
  };

  function initWebsocket() {
    console.log("initializing websocket");
    ws = new WebSocket(`ws${location.protocol === "https:" ? "s" : ""}://${location.host}/client`);

    let runs = {};

    ws.addEventListener("open", () => {
      ws.addEventListener("message", (event) => {
        const message = JSON.parse(event.data);
        console.log("< receiving", message);
        const { type, data } = message;

        const wasAtBottom = isScrollAtBottom();
        switch (type) {
          case "Run":
            handleRunMessage(data);
            break;
          case "Section":
            handleSectionMessage(data);
            break;
          case "Message":
            handleMessage(data);
            break;
          case "MessageStreamPart":
            handleMessageStreamPart(data);
            break;
          case "ToolCall":
            handleToolCall(data);
            break;
          case "ToolCallStreamPart":
            handleToolCallStreamPart(data);
            break;
          default:
            console.warn("Unknown message type:", type);
        }
        scrollUpdate(wasAtBottom);
      });

      function createRunListEntry(runId) {
        const runList = document.getElementById("run-list");
        const template = document.getElementById("run-list-entry-template");
        const runListEntry = template.content.cloneNode(true).querySelector(".run-list-entry");
        runListEntry.id = `run-list-entry-${runId}`;
        const a = runListEntry.querySelector("a");
        a.href = "#" + runId;
        a.addEventListener("click", () => {
          selectRun(runId);
        });
        runList.insertBefore(runListEntry, runList.firstChild);
        return runListEntry;
      }

      function handleRunMessage(run) {
        runs[run.id] = run;
        let li = document.getElementById(`run-list-entry-${run.id}`);
        if (!li) {
          li = createRunListEntry(run.id);
        }

        li.querySelector(".run-id").textContent = `Run ${run.id}`;
        li.querySelector(".run-model").tExtContent = run.model;
        li.querySelector(".run-tags").textContent = run.tag;
        li.querySelector(".run-started-at").textContent = run.started_at.slice(0, -10);
        if (run.stopped_at) {
          li.querySelector(".run-stopped-at").textContent = run.stopped_at.slice(0, -10);
        }
        li.querySelector(".run-state").textContent = run.state;

        const followNewRunsCheckbox = document.getElementById("follow_new_runs");
        if (followNewRunsCheckbox.checked) {
          selectRun(run.id);
        }
      }

      function addSectionDiv(sectionId) {
        const messagesDiv = document.getElementById("messages");
        const template = document.getElementById("section-template");
        const sectionDiv = template.content.cloneNode(true).querySelector(".section");
        sectionDiv.id = `section-${sectionId}`;
        messagesDiv.appendChild(sectionDiv);
        return sectionDiv;
      }

      let sectionStorage = {};
      let sectionColumns = [];

      // treat null as +infinity for comparisons
      const toOrInf = (x) => (x == null ? Number.POSITIVE_INFINITY : x);

      function rebuildSectionLayout() {
        // reset columns
        sectionColumns = [];

        // collect all current sections from storage
        const sections = Object.values(sectionStorage)
          .map((s) => s.section)
          .filter(Boolean);

        // sort so parents are processed before children:
        //  - by from_message ascending
        //  - then by to_message descending (longer span first)
        sections.sort((a, b) => {
          if (a.from_message !== b.from_message) {
            return a.from_message - b.from_message;
          }
          return b.to_message - a.to_message;
        });

        // id -> { column, position }
        const layout = {};

        for (const s of sections) {
          const sFrom = s.from_message;
          const sTo = toOrInf(s.to_message);

          // --- 1) find minimum allowed column because of parents ---
          let minCol = 0;

          for (let i = 0; i < sectionColumns.length; i++) {
            const column = sectionColumns[i];
            for (const other of column) {
              const oFrom = other.from_message;
              const oTo = toOrInf(other.to_message);

              // other is a parent if it fully contains s
              if (oFrom <= sFrom && sTo <= oTo) {
                minCol = Math.max(minCol, i + 1); // must be strictly to the right
              }
            }
          }

          // --- 2) place section into first non-overlapping column >= minCol ---
          let chosenCol = -1;
          for (let i = minCol; i < sectionColumns.length; i++) {
            const column = sectionColumns[i];
            let fits = true;

            for (const other of column) {
              const oFrom = other.from_message;
              const oTo = toOrInf(other.to_message);

              // standard interval overlap check
              if (sFrom < oTo && oFrom < sTo) {
                fits = false;
                break;
              }
            }

            if (fits) {
              chosenCol = i;
              column.push(s);
              break;
            }
          }

          // no existing column fits → create a new one
          if (chosenCol === -1) {
            chosenCol = sectionColumns.length;
            sectionColumns.push([s]);
          }

          const position = sectionColumns[chosenCol].length;
          // +1 for CSS grid columns (1-based)
          layout[s.id] = { column: chosenCol + 1, position };
        }

        // update CSS var with column count
        document.documentElement.style.setProperty(
          "--section-column-count",
          sectionColumns.length.toString()
        );

        // --- 3) apply layout to DOM & wire click handlers ---
        for (const s of sections) {
          const { column, position } = layout[s.id];

          let sectionDiv = document.getElementById(`section-${s.id}`);
          if (!sectionDiv) {
            sectionDiv = addSectionDiv(s.id);
          }

          sectionDiv.querySelector(".section-name").textContent = `${s.name}`;

          // grid position
          sectionDiv.style.gridColumn = column;
          sectionDiv.style.gridRow = `${s.from_message} / ${s.to_message}`;
          sectionDiv.setAttribute("columnNumber", column);
          sectionDiv.setAttribute("columnPosition", position);

          const storage = sectionStorage[s.id] || (sectionStorage[s.id] = {});

          // preserve open/closed if we had it before, default to open
          const open =
            storage.open ??
            (sectionDiv.getAttribute("opened") !== "false"); // default true
          storage.open = open;
          sectionDiv.setAttribute("opened", open.toString());

          // helper to sync all messages in the section with current open state
          const syncMessages = () => {
            for (let i = s.from_message; i <= s.to_message; i++) {
              const messageDiv = document.getElementById(`message-${i}`);
              if (messageDiv) {
                if (storage.open) {
                  messageDiv.setAttribute("open", "");
                } else {
                  messageDiv.removeAttribute("open");
                }
              }
            }
          };
          syncMessages();

          // (re)attach click handler
          if (storage.openingFunction) {
            sectionDiv.removeEventListener("click", storage.openingFunction);
          }

          storage.openingFunction = () => {
            storage.open = !storage.open;
            sectionDiv.setAttribute("opened", storage.open.toString());
            syncMessages();
          };

          sectionDiv.addEventListener("click", storage.openingFunction);
        }
      }

      function handleSectionMessage(section) {
        console.log("handling section message", section);

        // normalise *a copy* of the incoming section
        const normalized = { ...section };
        normalized.from_message += 1;
        if (normalized.to_message === null) {
          normalized.to_message = 99999;
        }
        normalized.to_message += 1;

        if (!sectionStorage[normalized.id]) {
          sectionStorage[normalized.id] = {};
        }
        sectionStorage[normalized.id].section = normalized;

        // recompute layout for all sections
        rebuildSectionLayout();
      }

      function addMessageDiv(messageId, role) {
        const messagesDiv = document.getElementById("messages");
        const template = document.getElementById("message-template");
        const messageDiv = template.content.cloneNode(true).querySelector(".message");

        messageDiv.id = `message-${messageId}`;
        messageDiv.style = `grid-row: ${messageId + 1};`;
        if (role === "system" || role === "limit") {
          messageDiv.removeAttribute("open");
        }
        messageDiv.querySelector(".tool-calls").id = `message-${messageId}-tool-calls`;
        messagesDiv.appendChild(messageDiv);
        return messageDiv;
      }

      function handleMessage(message) {
        let messageDiv = document.getElementById(`message-${message.id}`);
        if (!messageDiv) {
          messageDiv = addMessageDiv(message.id, message.role);
        }
        messageDiv.querySelector(".role").textContent = message.role;
        if (message.duration > 0) {
          messageDiv.querySelector(".duration").textContent = `${message.duration.toFixed(3)} s`;
        }
        console.log(message.tokens_query, typeof message.tokens_query);
        if (message.tokens_query > 0) {
          messageDiv.querySelector(".tokens-query").textContent = `${message.tokens_query} qry tokens`;
        }
        let tokens_ctr = 0;
        if (message.tokens_response) {
          messageDiv.querySelector(".tokens-response").textContent = `${message.tokens_response} rsp tokens`;
          tokens_ctr++;
        }
        if (message.tokens_reasoning) {
          messageDiv.querySelector(".tokens-reasoning").textContent = `${message.tokens_reasoning} reason tokens`;
          tokens_ctr++;
        }
        if (tokens_ctr == 2) {
          messageDiv.querySelector(".tokens-separator").textContent = " - ";
        }
        if (message.content && message.content.length > 0) {
          if (message.role === "limit" && message.tokens_query <= 0) {
            messageDiv.querySelector(".tokens-query").textContent = message.content.split(":", 2)[1];
          }
          messageDiv.querySelector(".message-text").textContent = message.content;
        }
        if (message.reasoning && message.reasoning.length > 0) {
          const reasoningDiv = messageDiv.querySelector(".reasoning");
          reasoningDiv.style.display = "block";
          const reasoningTextDiv = reasoningDiv.querySelector(".reasoning-text");
          reasoningTextDiv.textContent = message.reasoning;
        }
      }

      function handleMessageStreamPart(part) {
        let messageDiv = document.getElementById(`message-${part.message_id}`);
        if (!messageDiv) {
          messageDiv = addMessageDiv(part.message_id);
        }
        messageDiv.querySelector(".message-text").textContent += part.content;
        if(part.reasoning && part.reasoning.length > 0) {
          const reasoningDiv = messageDiv.querySelector(".reasoning");
          reasoningDiv.style.display = "block";
          const reasoningTextDiv = reasoningDiv.querySelector(".reasoning-text");
          reasoningTextDiv.textContent += part.reasoning;
        }
      }

      function addToolCallDiv(messageId, toolCallId, functionName) {
        const toolCallsDiv = document.getElementById(`message-${messageId}-tool-calls`);
        const template = document.getElementById("message-tool-call");
        const toolCallDiv = template.content.cloneNode(true).querySelector(".tool-call");

        toolCallDiv.id = `message-${messageId}-tool-call-${toolCallId}`;
        toolCallDiv.querySelector(".tool-call-function").textContent = functionName;
        toolCallsDiv.appendChild(toolCallDiv);

        return toolCallDiv;
      }

      function handleToolCall(toolCall) {
        let toolCallDiv = document.getElementById(`message-${toolCall.message_id}-tool-call-${toolCall.id}`);
        if (!toolCallDiv) {
          toolCallDiv = addToolCallDiv(
            toolCall.message_id,
            toolCall.id,
            toolCall.function_name,
          );
        }
        toolCallDiv.querySelector(".tool-call-state").textContent = toolCall.state;
        toolCallDiv.querySelector(".tool-call-duration").textContent = `${toolCall.duration.toFixed(3)} s`;
        toolCallDiv.querySelector(".tool-call-parameters").textContent = toolCall.arguments;
        toolCallDiv.querySelector(".tool-call-results").textContent = toolCall.result_text;
      }

      function handleToolCallStreamPart(part) {
        const messageDiv = document.getElementById(`message-${part.message_id}-tool-calls`);
        if (messageDiv) {
          let toolCallDiv = messageDiv.querySelector(`.tool-call-${part.tool_call_id}`);
          if (!toolCallDiv) {
            toolCallDiv = document.createElement("div");
            toolCallDiv.className = `tool-call tool-call-${part.tool_call_id}`;
            messageDiv.appendChild(toolCallDiv);
          }
          toolCallDiv.textContent += part.content;
        }
      }

      const selectRun = debounce((runId) => {
        if (runId === currentRun) {
          return;
        }

        document.getElementById("messages").innerHTML = "";
        sectionColumns = [];
        sectionStorage = {};
        document.documentElement.style.setProperty("--section-column-count", 0);
        send("MessageRequest", { follow_run: runId });
        currentRun = runId;
        // set hash to runId via pushState
        window.location.hash = runId;
        sidebar.classList.remove("active");
        document.getElementById("main-run-title").textContent = `Run ${runId}`;

        // try to json parse and pretty print the run configuration into `#run-config`
        try {
          const config = JSON.parse(runs[runId].configuration);
          document.getElementById("run-config").textContent = JSON.stringify(config, null, 2);
        } catch (e) {
          document.getElementById("run-config").textContent = runs[runId].configuration;
        }
      });
      if (window.location.hash) {
        selectRun(parseInt(window.location.hash.slice(1), 10));
      } else {
        // toggle the sidebar if no run is selected
        sidebar.classList.add("active");
        document.getElementById("main-run-title").textContent = "Please select a run";
      }

      ws.addEventListener("close", initWebsocket);
    });
  }

  initWebsocket();
})();
