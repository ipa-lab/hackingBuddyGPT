/* jshint esversion: 9, browser: true */
/* global console */

(function() {
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
    console.log(
        "scroll check",
        content.scrollHeight,
        content.scrollTop,
        content.clientHeight,
    );
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
  let followNewRuns =
      !window.location.hash && localStorage.getItem("followNewRuns") === "true";
  followNewRunsCheckbox.checked = followNewRuns;

  followNewRunsCheckbox.addEventListener("change", () => {
    followNewRuns = followNewRunsCheckbox.checked;
    localStorage.setItem("followNewRuns", followNewRuns);
  });

  let send = function (type, data) {
    const message = {type: type, data: data};
    console.log("> sending  ", message);
    ws.send(JSON.stringify(message));
  };

  function initWebsocket() {
    console.log("initializing websocket");
    ws = new WebSocket(
        `ws${location.protocol === "https:" ? "s" : ""}://${location.host}/client`,
    );

    let runs = {};

    ws.addEventListener("open", () => {
      ws.addEventListener("message", (event) => {
        const message = JSON.parse(event.data);
        console.log("< receiving", message);
        const {type, data} = message;

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
        const runListEntry = template.content
            .cloneNode(true)
            .querySelector(".run-list-entry");
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
        li.querySelector(".run-started-at").textContent = run.started_at.slice(
            0,
            -3,
        );
        if (run.stopped_at) {
          li.querySelector(".run-stopped-at").textContent = run.stopped_at.slice(
              0,
              -3,
          );
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
        const sectionDiv = template.content
            .cloneNode(true)
            .querySelector(".section");
        sectionDiv.id = `section-${sectionId}`;
        messagesDiv.appendChild(sectionDiv);
        return sectionDiv;
      }

      let sectionColumns = [];

      function handleSectionMessage(section) {
        console.log("handling section message", section);
        section.from_message += 1;
        if (section.to_message === null) {
          section.to_message = 99999;
        }
        section.to_message += 1;

        let sectionDiv = document.getElementById(`section-${section.id}`);
        if (!!sectionDiv) {
          let columnNumber = sectionDiv.getAttribute("columnNumber");
          let columnPosition = sectionDiv.getAttribute("columnPosition");
          sectionColumns[columnNumber].splice(columnPosition - 1, 1);
          sectionDiv.remove();
        }
        sectionDiv = addSectionDiv(section.id);
        sectionDiv.querySelector(".section-name").textContent =
            `${section.name} ${section.duration.toFixed(3)}s`;

        let columnNumber = 0;
        let columnPosition = 0;

        // loop over the existing section Columns (format is a list of lists, whereby the inner list is [from_message, from_message], with end_message possibly being None)
        let found = false;
        for (let i = 0; i < sectionColumns.length; i++) {
          const column = sectionColumns[i];
          let columnFits = true;
          for (let j = 0; j < column.length; j++) {
            const [from_message, to_message] = column[j];
            if (
                section.from_message < to_message &&
                from_message < section.to_message
            ) {
              columnFits = false;
              break;
            }
          }
          if (!columnFits) {
            continue;
          }

          column.push([section.from_message, section.to_message]);
          columnNumber = i;
          columnPosition = column.length;
          found = true;
          break;
        }
        if (!found) {
          sectionColumns.push([[section.from_message, section.to_message]]);
          document.documentElement.style.setProperty(
              "--section-column-count",
              sectionColumns.length,
          );
          console.log(
              "added section column",
              sectionColumns.length,
              sectionColumns,
          );
        }

        sectionDiv.style = `grid-column: ${columnNumber}; grid-row: ${section.from_message} / ${section.to_message};`;
        sectionDiv.setAttribute("columnNumber", columnNumber);
        sectionDiv.setAttribute("columnPosition", columnPosition);
      }

      function addMessageDiv(messageId, role) {
        const messagesDiv = document.getElementById("messages");
        const template = document.getElementById("message-template");
        const messageDiv = template.content
            .cloneNode(true)
            .querySelector(".message");
        messageDiv.id = `message-${messageId}`;
        messageDiv.style = `grid-row: ${messageId + 1};`;
        if (role === "system") {
          messageDiv.removeAttribute("open");
        }
        messageDiv.querySelector(".tool-calls").id =
            `message-${messageId}-tool-calls`;
        messagesDiv.appendChild(messageDiv);
        return messageDiv;
      }

      function handleMessage(message) {
        let messageDiv = document.getElementById(`message-${message.id}`);
        if (!messageDiv) {
          messageDiv = addMessageDiv(message.id, message.role);
        }
        if (message.content && message.content.length > 0) {
          messageDiv.getElementsByTagName("pre")[0].textContent = message.content;
        }
        messageDiv.querySelector(".role").textContent = message.role;
        messageDiv.querySelector(".duration").textContent =
            `${message.duration.toFixed(3)} s`;
        messageDiv.querySelector(".tokens-query").textContent =
            `${message.tokens_query} qry tokens`;
        messageDiv.querySelector(".tokens-response").textContent =
            `${message.tokens_response} rsp tokens`;
      }

      function handleMessageStreamPart(part) {
        let messageDiv = document.getElementById(`message-${part.message_id}`);
        if (!messageDiv) {
          messageDiv = addMessageDiv(part.message_id);
        }
        messageDiv.getElementsByTagName("pre")[0].textContent += part.content;
      }

      function addToolCallDiv(messageId, toolCallId, functionName) {
        const toolCallsDiv = document.getElementById(
            `message-${messageId}-tool-calls`,
        );
        const template = document.getElementById("message-tool-call");
        const toolCallDiv = template.content
            .cloneNode(true)
            .querySelector(".tool-call");
        toolCallDiv.id = `message-${messageId}-tool-call-${toolCallId}`;
        toolCallDiv.querySelector(".tool-call-function").textContent =
            functionName;
        toolCallsDiv.appendChild(toolCallDiv);
        return toolCallDiv;
      }

      function handleToolCall(toolCall) {
        let toolCallDiv = document.getElementById(
            `message-${toolCall.message_id}-tool-call-${toolCall.id}`,
        );
        if (!toolCallDiv) {
          toolCallDiv = addToolCallDiv(
              toolCall.message_id,
              toolCall.id,
              toolCall.function_name,
          );
        }
        toolCallDiv.querySelector(".tool-call-state").textContent =
            toolCall.state;
        toolCallDiv.querySelector(".tool-call-duration").textContent =
            `${toolCall.duration.toFixed(3)} s`;
        toolCallDiv.querySelector(".tool-call-parameters").textContent =
            toolCall.arguments;
        toolCallDiv.querySelector(".tool-call-results").textContent =
            toolCall.result_text;
      }

      function handleToolCallStreamPart(part) {
        const messageDiv = document.getElementById(
            `message-${part.message_id}-tool-calls`,
        );
        if (messageDiv) {
          let toolCallDiv = messageDiv.querySelector(
              `.tool-call-${part.tool_call_id}`,
          );
          if (!toolCallDiv) {
            toolCallDiv = document.createElement("div");
            toolCallDiv.className = `tool-call tool-call-${part.tool_call_id}`;
            messageDiv.appendChild(toolCallDiv);
          }
          toolCallDiv.textContent += part.content;
        }
      }

      const selectRun = debounce((runId) => {
        console.error("selectRun", runId, currentRun);
        if (runId === currentRun) {
          return;
        }

        document.getElementById("messages").innerHTML = "";
        sectionColumns = [];
        document.documentElement.style.setProperty("--section-column-count", 0);
        send("MessageRequest", {follow_run: runId});
        currentRun = runId;
        // set hash to runId via pushState
        window.location.hash = runId;
        sidebar.classList.remove("active");
        document.getElementById("main-run-title").textContent = `Run ${runId}`;

        // try to json parse and pretty print the run configuration into `#run-config`
        try {
          const config = JSON.parse(runs[runId].configuration);
          document.getElementById("run-config").textContent = JSON.stringify(
              config,
              null,
              2,
          );
        } catch (e) {
          document.getElementById("run-config").textContent =
              runs[runId].configuration;
        }
      });
      if (window.location.hash) {
        selectRun(parseInt(window.location.hash.slice(1), 10));
      } else {
        // toggle the sidebar if no run is selected
        sidebar.classList.add("active");
        document.getElementById("main-run-title").textContent =
            "Please select a run";
      }

      ws.addEventListener("close", initWebsocket);
    });
  }

  initWebsocket();
})();