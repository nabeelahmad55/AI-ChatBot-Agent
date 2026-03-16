document.addEventListener("DOMContentLoaded", () => {
  const API_BASE = "http://127.0.0.1:5000";

  let sessionId = null;
  let gptMessages = [];
  let countdownTimer = null;
  let isConversationComplete = false;
  let isAIThinking = false;

  const chatContainer = document.getElementById("chatContainer");
  const chatBox = document.getElementById("chatBox");
  const sendBtn = document.getElementById("sendBtn");
  const userInput = document.getElementById("userInput");
  const chatToggle = document.getElementById("chatToggle");
  const chatWidget = document.getElementById("chatWidget");
  const closeChat = document.getElementById("closeChat");

  initializeChat();

  function initializeChat() {
    localStorage.removeItem("chatOpen");
    localStorage.removeItem("sessionId");
    localStorage.removeItem("agentName");
    localStorage.removeItem("chatMessages");
    localStorage.removeItem("gptMessages");

    resetChatUI();
    autoStartChat();
  }

  function resetChatUI() {
    chatWidget.classList.remove('open');
    chatToggle.style.display = 'block';
    chatContainer.classList.add("d-none");
    chatBox.innerHTML = "Starting chat with Nabeel Ahmad...";
    gptMessages = [];
    sessionId = null;
    isConversationComplete = false;
    isAIThinking = false;
    clearCountdownTimer();
    enableChatInput();
  }

  async function autoStartChat() {
    try {
      const res = await fetch(`${API_BASE}/initialize_session`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ agent_name: "Nabeel Ahmad" }),
      });

      if (!res.ok) throw new Error("Failed to create session");
      const data = await res.json();
      
      sessionId = data.session_id;
      const initialMessage = data.ai_response;

      chatContainer.classList.remove("d-none");
      chatBox.innerHTML = "";
      gptMessages = [];

      appendMessage("assistant", initialMessage);
      
      gptMessages = [
        { role: "assistant", content: initialMessage }
      ];

      localStorage.setItem("sessionId", sessionId);
      localStorage.setItem("agentName", "Nabeel Ahmad");
      localStorage.setItem("chatMessages", JSON.stringify([
        { role: "assistant", text: initialMessage }
      ]));
      localStorage.setItem("gptMessages", JSON.stringify(gptMessages));

    } catch (err) {
      chatBox.innerHTML = "Error starting chat with Nabeel Ahmad. Please check backend connection.";
    }
  }

  function clearCountdownTimer() {
    if (countdownTimer) {
      clearInterval(countdownTimer);
      countdownTimer = null;
    }
  }

  function startCountdownTimer() {
    let countdown = 20;
    
    const countdownDiv = document.createElement("div");
    countdownDiv.className = "countdown-message system-message";
    countdownDiv.id = "countdownTimer";
    countdownDiv.innerHTML = `<b>SYSTEM:</b><br>Chat will close automatically in <span id="countdownNumber">${countdown}</span> seconds...`;
    chatBox.appendChild(countdownDiv);
    
    chatBox.scrollTop = chatBox.scrollHeight;
    disableChatInput();
    
    countdownTimer = setInterval(() => {
      countdown--;
      const countdownElement = document.getElementById("countdownNumber");
      
      if (countdownElement) {
        countdownElement.textContent = countdown;
      }
      
      if (countdown <= 0) {
        clearCountdownTimer();
        closeChatWidget();
      }
    }, 1000);
  }

  function disableChatInput() {
    userInput.disabled = true;
    sendBtn.disabled = true;
    userInput.placeholder = "Please wait...";
    isAIThinking = true;
  }

  function enableChatInput() {
    userInput.disabled = false;
    sendBtn.disabled = false;
    userInput.placeholder = "Type message...";
    isAIThinking = false;
  }

  function openChat() {
    chatWidget.classList.add('open');
    chatToggle.style.display = 'none';
    localStorage.setItem("chatOpen", "true");
    restoreChat();
  }

  function restoreChat() {
    const savedChat = JSON.parse(localStorage.getItem("chatMessages") || "[]");
    sessionId = localStorage.getItem("sessionId") || null;
    gptMessages = JSON.parse(localStorage.getItem("gptMessages") || "[]");

    if (sessionId) {
      chatContainer.classList.remove("d-none");
    }
    
    if (sessionId && savedChat.length > 0) {
      chatBox.innerHTML = "";
      savedChat.forEach(msg => appendMessage(msg.role, msg.text, false));
    } else if (!sessionId) {
      autoStartChat();
    }

    setTimeout(() => {
      chatBox.scrollTop = chatBox.scrollHeight;
    }, 100);
  }

  function closeChatWidget() {
    if (!isConversationComplete) {
      const warningDiv = document.createElement("div");
      warningDiv.className = "warning-message system-message";
      warningDiv.innerHTML = `<b>SYSTEM:</b><br>Please complete the conversation with Quartz AI before closing the chat.`;
      chatBox.appendChild(warningDiv);
      
      chatBox.scrollTop = chatBox.scrollHeight;
      
      setTimeout(() => {
        if (warningDiv.parentNode) {
          warningDiv.remove();
        }
      }, 3000);
      
      return;
    }
    
    clearCountdownTimer();
    chatWidget.classList.remove('open');
    chatToggle.style.display = 'block';
    localStorage.setItem("chatOpen", "false");
    enableChatInput();
  }

  sendBtn.addEventListener("click", async () => {
    const text = userInput.value.trim();
    if (!text || !sessionId || isAIThinking) {
      return;
    }

    appendMessage("user", text);
    userInput.value = "";
    resetTextareaHeight();

    gptMessages.push({ role: "user", content: text });
    disableChatInput();

    try {
      const res = await fetch(`${API_BASE}/chat_with_ai`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: gptMessages,
          session_id: sessionId,
          agent_name: "Nabeel Ahmad"
        }),
      });

      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      
      const data = await res.json();
      const reply = data.response || "No response received.";
      
      if (reply.includes("CONVERSATION_END:")) {
        isConversationComplete = true;
        const displayReply = reply.replace("CONVERSATION_END:", "").trim();
        appendMessage("assistant", displayReply);
        gptMessages.push({ role: "assistant", content: reply });
        
        setTimeout(() => {
          startCountdownTimer();
        }, 1000);
      } else {
        appendMessage("assistant", reply);
        gptMessages.push({ role: "assistant", content: reply });
      }
    } catch (err) {
      appendMessage("assistant", "⚠️ Error communicating with backend.");
    } finally {
      if (!isConversationComplete) {
        enableChatInput();
      }
    }
  });

  function autoExpandTextarea() {
    userInput.style.height = 'auto';
    const newHeight = Math.min(userInput.scrollHeight, 120);
    userInput.style.height = newHeight + 'px';
    userInput.style.overflowY = newHeight >= 120 ? 'auto' : 'hidden';
  }

  function resetTextareaHeight() {
    userInput.style.height = '44px';
    userInput.style.overflowY = 'hidden';
  }

  userInput.addEventListener('input', autoExpandTextarea);

  userInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendBtn.click();
    }
  });

  function appendMessage(role, text, save = true) {
    if (chatBox.innerHTML === "Starting chat with Agent 1..." || chatBox.innerHTML === "Chat will appear here once started.") {
      chatBox.innerHTML = "";
    }
    
    const div = document.createElement("div");
    div.className = `message ${role}-message`;
    
    const label = role === "user" ? "AGENT" : "QUARTZ AI";
    div.innerHTML = `<b>${label}:</b><br>${text.replace(/\n/g, "<br>")}`;
    chatBox.appendChild(div);

    chatBox.scrollTop = chatBox.scrollHeight;

    if (save) {
      const saved = JSON.parse(localStorage.getItem("chatMessages") || "[]");
      saved.push({ role, text });
      localStorage.setItem("chatMessages", JSON.stringify(saved));
      localStorage.setItem("gptMessages", JSON.stringify(gptMessages));
    }
  }

  chatToggle.addEventListener("click", function() {
    openChat();
  });

  closeChat.addEventListener("click", function(e) {
    e.preventDefault();
    e.stopPropagation();
    closeChatWidget();
  });

  const wasChatOpen = localStorage.getItem("chatOpen") === "true";
  if (wasChatOpen) {
    openChat();
  }
});