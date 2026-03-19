const authScreen = document.getElementById("auth-screen");
const appShell = document.getElementById("app-shell");
const authForm = document.getElementById("auth-form");
const authUsernameInput = document.getElementById("auth-username");
const authPasswordInput = document.getElementById("auth-password");
const authStatus = document.getElementById("auth-status");
const authSubmitButton = document.getElementById("auth-submit");
const authModeToggle = document.getElementById("auth-mode-toggle");
const loginModeButton = document.getElementById("login-mode-button");
const registerModeButton = document.getElementById("register-mode-button");
const logoutButton = document.getElementById("logout-button");
const userAvatar = document.getElementById("user-avatar");
const userName = document.getElementById("user-name");

const form = document.getElementById("chat-form");
const questionInput = document.getElementById("question");
const sendButton = document.getElementById("send-button");
const newChatButton = document.getElementById("new-chat-button");
const personaToggleButton = document.getElementById("persona-toggle");
const personaMenu = document.getElementById("persona-menu");
const personaOptions = Array.from(document.querySelectorAll(".persona-option"));
const messagesScroll = document.getElementById("messages-scroll");
const messages = document.getElementById("messages");
const statusText = document.getElementById("status");
const messageTemplate = document.getElementById("message-template");
const historyList = document.getElementById("chat-history");
const emptyState = document.getElementById("empty-state");
const assistantLabel = document.getElementById("assistant-label");
const assistantTitle = document.getElementById("assistant-title");
const emptyStateKicker = document.getElementById("empty-state-kicker");
const emptyStateTitle = document.getElementById("empty-state-title");
const emptyStateDescription = document.getElementById("empty-state-description");

let authMode = "login";
let currentUser = null;
let activeRequestController = null;
let conversations = [];
let activeConversationId = null;
let activePersona = "accountant";

const PERSONAS = {
    accountant: {
        name: "Accountant Assistant",
        shortName: "Accountant",
        avatar: "AO",
        headerTitle: "AccountantGPT",
        kicker: "Grounded answers from your indexed PDFs",
        emptyTitle: "Whenever you need it.",
        emptyDescription:
            "Ask about accounting rules, classifications, and references from the uploaded document set.",
        toggleClass: "bg-sky-400/10 text-sky-300 hover:bg-sky-400/15",
    },
    ai: {
        name: "AI Assistant",
        shortName: "AI",
        avatar: "AI",
        headerTitle: "AI Assistant",
        kicker: "General model help without PDF grounding",
        emptyTitle: "Ready to help.",
        emptyDescription:
            "Ask broader questions and get model-based answers even when the document set is not relevant.",
        toggleClass: "bg-white/5 text-zinc-300 hover:bg-white/10",
    },
};

function apiFetch(url, options = {}) {
    return fetch(url, {
        credentials: "same-origin",
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {}),
        },
    });
}

function autoResizeTextarea() {
    questionInput.style.height = "auto";
    questionInput.style.height = `${Math.min(questionInput.scrollHeight, 220)}px`;
}

function scrollMessagesToBottom() {
    requestAnimationFrame(() => {
        messagesScroll.scrollTop = messagesScroll.scrollHeight;
    });
}

function getInitials(value) {
    const normalized = (value || "").trim();
    return normalized.slice(0, 2).toUpperCase() || "--";
}

function escapeHtml(value) {
    return (value || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function renderInlineMarkdown(text) {
    let html = escapeHtml(text);
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");
    html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>');
    return html;
}

function renderMarkdown(text) {
    const normalized = (text || "").replace(/\r\n/g, "\n");
    const codeBlocks = [];

    const withPlaceholders = normalized.replace(/```([\w-]*)\n?([\s\S]*?)```/g, (_, language, code) => {
        const index = codeBlocks.length;
        const languageLabel = language ? `<div class="mb-2 text-[0.72rem] uppercase tracking-[0.08em] text-zinc-500">${escapeHtml(language)}</div>` : "";
        codeBlocks.push(
            `<pre><code>${languageLabel}${escapeHtml(code.trimEnd())}</code></pre>`
        );
        return `@@CODEBLOCK_${index}@@`;
    });

    const blocks = withPlaceholders.split(/\n\s*\n/).filter(Boolean);
    const html = blocks.map((block) => {
        if (/^@@CODEBLOCK_\d+@@$/.test(block.trim())) {
            return block.trim();
        }

        const lines = block.split("\n");
        if (lines.every((line) => /^[-*]\s+/.test(line))) {
            const items = lines
                .map((line) => `<li>${renderInlineMarkdown(line.replace(/^[-*]\s+/, ""))}</li>`)
                .join("");
            return `<ul>${items}</ul>`;
        }

        if (lines.every((line) => /^\d+\.\s+/.test(line))) {
            const items = lines
                .map((line) => `<li>${renderInlineMarkdown(line.replace(/^\d+\.\s+/, ""))}</li>`)
                .join("");
            return `<ol>${items}</ol>`;
        }

        if (block.startsWith(">")) {
            const quote = lines.map((line) => line.replace(/^>\s?/, "")).join("\n");
            return `<blockquote>${renderInlineMarkdown(quote).replace(/\n/g, "<br>")}</blockquote>`;
        }

        if (/^#{1,3}\s+/.test(lines[0])) {
            const level = Math.min((lines[0].match(/^#+/)[0] || "").length, 3);
            const content = renderInlineMarkdown(lines.join(" ").replace(/^#{1,3}\s+/, ""));
            return `<h${level}>${content}</h${level}>`;
        }

        return `<p>${lines.map((line) => renderInlineMarkdown(line)).join("<br>")}</p>`;
    }).join("");

    return html.replace(/@@CODEBLOCK_(\d+)@@/g, (_, index) => codeBlocks[Number(index)] || "");
}

function setAuthMode(mode) {
    authMode = mode;
    const isLogin = mode === "login";
    loginModeButton.className = `relative z-10 flex-1 cursor-pointer rounded-[14px] px-3 py-2 text-sm font-medium transition pointer-events-auto ${
        isLogin ? "bg-zinc-100 text-zinc-950" : "text-zinc-300"
    }`;
    registerModeButton.className = `relative z-10 flex-1 cursor-pointer rounded-[14px] px-3 py-2 text-sm font-medium transition pointer-events-auto ${
        isLogin ? "text-zinc-300" : "bg-zinc-100 text-zinc-950"
    }`;
    loginModeButton.setAttribute("aria-pressed", String(isLogin));
    registerModeButton.setAttribute("aria-pressed", String(!isLogin));
    authSubmitButton.textContent = isLogin ? "Sign in" : "Create account";
    authStatus.textContent = "";
}

function showAuthScreen() {
    authScreen.classList.remove("hidden");
    appShell.classList.add("hidden");
    appShell.classList.remove("grid");
}

function showAppShell() {
    authScreen.classList.add("hidden");
    appShell.classList.remove("hidden");
    appShell.classList.add("grid");
}

function setCurrentUser(user) {
    currentUser = user;
    userName.textContent = user?.username || "User";
}

function getPersonaConfig(persona) {
    return PERSONAS[persona] || PERSONAS.accountant;
}

function inferMessagePersona(message) {
    if (message.persona) {
        return message.persona;
    }
    return message.context?.length || message.sources?.length ? "accountant" : "ai";
}

function closePersonaMenu() {
    personaMenu.classList.add("hidden");
    personaMenu.classList.remove("flex");
}

function updatePersonaOptions() {
    personaOptions.forEach((option) => {
        const isActive = option.dataset.persona === activePersona;
        const baseClass =
            "persona-option flex min-h-[420px] flex-col overflow-hidden rounded-[26px] text-left transition";
        const themeClass = isActive
            ? "border border-sky-400/65 bg-[#232323]/92 shadow-[0_0_0_1px_rgba(56,189,248,0.2),0_16px_36px_rgba(0,0,0,0.22)]"
            : "border border-white/10 bg-[#232323]/92 hover:border-white/20";
        option.className = `${baseClass} ${themeClass}`;
    });
}

function setActivePersona(persona) {
    activePersona = PERSONAS[persona] ? persona : "accountant";
    const config = getPersonaConfig(activePersona);
    personaToggleButton.setAttribute("aria-pressed", "true");
    personaToggleButton.className = `inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-[0.8rem] font-medium transition ${config.toggleClass}`;
    personaToggleButton.textContent = config.name;
    assistantLabel.textContent = config.shortName;
    assistantTitle.textContent = config.headerTitle;
    emptyStateKicker.textContent = config.kicker;
    emptyStateTitle.textContent = config.emptyTitle;
    emptyStateDescription.textContent = config.emptyDescription;
    updatePersonaOptions();
}

function sortConversations() {
    conversations.sort((left, right) => right.updated_at.localeCompare(left.updated_at));
}

function getActiveConversation() {
    return conversations.find((conversation) => conversation.id === activeConversationId) || null;
}

function upsertConversation(conversation) {
    const existingIndex = conversations.findIndex((item) => item.id === conversation.id);
    if (existingIndex >= 0) {
        conversations[existingIndex] = { ...conversations[existingIndex], ...conversation };
    } else {
        conversations.push(conversation);
    }
    sortConversations();
}

function buildContextToggle(message) {
    const hasSources = message.sources?.length;
    const hasContext = message.context?.length;
    if (!hasSources && !hasContext) {
        return null;
    }

    const details = document.createElement("details");
    details.className = "context-toggle mb-3";

    const summary = document.createElement("summary");
    summary.className =
        "inline-flex cursor-pointer list-none items-center gap-2 rounded-full bg-sky-400/10 px-3 py-1.5 text-[0.78rem] font-medium text-sky-300 transition hover:bg-sky-400/15";
    summary.textContent = "Context";

    const panel = document.createElement("div");
    panel.className =
        "mt-3 rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm leading-6 text-zinc-300";

    if (hasSources) {
        const sourcesTitle = document.createElement("div");
        sourcesTitle.className = "mb-1 text-[0.72rem] uppercase tracking-[0.08em] text-zinc-500";
        sourcesTitle.textContent = "Sources";
        panel.appendChild(sourcesTitle);

        const sourcesText = document.createElement("p");
        sourcesText.className = "mb-3";
        sourcesText.textContent = message.sources.join(", ");
        panel.appendChild(sourcesText);
    }

    if (hasContext) {
        const contextTitle = document.createElement("div");
        contextTitle.className = "mb-1 text-[0.72rem] uppercase tracking-[0.08em] text-zinc-500";
        contextTitle.textContent = "Retrieved context";
        panel.appendChild(contextTitle);

        const list = document.createElement("ul");
        list.className = "m-0 list-disc pl-[18px]";

        message.context.slice(0, 3).forEach((doc) => {
            const item = document.createElement("li");
            const page = doc.page ? ` page ${doc.page}` : "";
            const excerpt = doc.content.slice(0, 220);
            const suffix = doc.content.length > 220 ? "..." : "";
            item.textContent = `${doc.source}${page}: ${excerpt}${suffix}`;
            list.appendChild(item);
        });

        panel.appendChild(list);
    }

    details.append(summary, panel);
    return details;
}

function renderMessage(message) {
    const fragment = messageTemplate.content.cloneNode(true);
    const article = fragment.querySelector(".message");
    const avatar = fragment.querySelector(".message-avatar");
    const meta = fragment.querySelector(".message-meta");
    const body = fragment.querySelector(".message-body");
    const content = fragment.querySelector(".message-content");

    const isUser = message.role === "user";
    const persona = inferMessagePersona(message);
    const personaConfig = getPersonaConfig(persona);
    article.className = `message grid gap-3.5 ${
        isUser
            ? "message-user ml-auto w-full max-w-[820px] grid-cols-[minmax(0,1fr)] items-end"
            : "message-assistant w-full max-w-[820px] grid-cols-[42px_minmax(0,1fr)] items-start"
    }`;
    avatar.textContent = isUser ? getInitials(currentUser?.username || "Y") : personaConfig.avatar;
    meta.textContent = isUser ? currentUser?.username || "You" : personaConfig.name;
    body.innerHTML = renderMarkdown(message.content || "");
    avatar.className = `message-avatar grid h-[34px] w-[34px] place-items-center rounded-xl text-[0.8rem] font-bold ${
        isUser
            ? "bg-zinc-200 text-zinc-950"
            : persona === "accountant"
              ? "bg-sky-300 text-sky-950"
              : "bg-zinc-700 text-white"
    }`;
    if (isUser) {
        avatar.remove();
        content.style.gridColumn = "1";
        content.className = "message-content min-w-0 pt-0.5 text-right";
        meta.className =
            "message-meta mb-2.5 text-[0.74rem] uppercase tracking-[0.08em] text-zinc-500";
        body.className =
            "message-body markdown-body ml-auto inline-block max-w-[85%] rounded-[26px] bg-[#343541] px-4 py-3 text-left text-[15px] leading-7 text-zinc-100";
    } else {
        avatar.style.gridColumn = "1";
        content.style.gridColumn = "2";
        content.className = "message-content min-w-0 max-w-[78ch] pt-0.5";
        meta.className =
            "message-meta mb-2.5 text-[0.74rem] uppercase tracking-[0.08em] text-zinc-500";
        body.className =
            "message-body markdown-body text-[15px] leading-7 text-zinc-100";
    }

    const contextToggle = !isUser ? buildContextToggle(message) : null;
    if (contextToggle) {
        content.insertBefore(contextToggle, body);
    }

    return article;
}

function updateHistory() {
    historyList.innerHTML = "";

    conversations.forEach((conversation) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "history-item rounded-xl px-3 py-2.5 text-left text-sm transition";
        if (conversation.id === activeConversationId) {
            button.classList.add("bg-panelSoft", "text-zinc-100");
        } else {
            button.classList.add("bg-transparent", "text-zinc-300", "hover:bg-panelHover");
        }

        button.textContent = conversation.title;
        button.addEventListener("click", async () => {
            await loadConversation(conversation.id);
        });
        historyList.appendChild(button);
    });
}

function renderConversation() {
    const conversation = getActiveConversation();
    messages.innerHTML = "";

    const hasMessages = Boolean(conversation?.messages?.length);
    emptyState.classList.toggle("hidden", hasMessages);
    messagesScroll.classList.toggle("hidden", !hasMessages);

    if (!conversation) {
        updateHistory();
        return;
    }

    (conversation.messages || []).forEach((message) => {
        messages.appendChild(renderMessage(message));
    });

    scrollMessagesToBottom();
    updateHistory();
}

function appendConversationMessage(message) {
    const conversation = getActiveConversation();
    if (!conversation) {
        return null;
    }

    conversation.messages = conversation.messages || [];
    conversation.messages.push(message);
    if (conversation.messages.length === 1 && message.role === "user") {
        conversation.title = message.content.slice(0, 30) || "New conversation";
    }
    conversation.updated_at = new Date().toISOString();

    sortConversations();
    renderConversation();
    return messages.lastElementChild;
}

function createAssistantMessage() {
    return appendConversationMessage({ role: "assistant", persona: activePersona, content: " " });
}

function updateAssistantMessage(article, content) {
    if (!article) {
        return;
    }

    article.querySelector(".message-body").innerHTML = renderMarkdown(content || "");
    scrollMessagesToBottom();
}

function renderAssistantMetadata(article, options = {}) {
    if (!article) {
        return;
    }

    article.querySelector(".context-toggle")?.remove();

    const contextToggle = buildContextToggle({
        sources: options.sources || [],
        context: options.context || [],
    });
    if (contextToggle) {
        const content = article.querySelector(".message-content");
        const body = article.querySelector(".message-body");
        content.insertBefore(contextToggle, body);
    }
    scrollMessagesToBottom();
}

async function createConversation() {
    const response = await apiFetch("/api/chat/conversations", { method: "POST" });
    if (!response.ok) {
        throw new Error("Could not create the conversation.");
    }

    const conversation = await response.json();
    upsertConversation(conversation);
    activeConversationId = conversation.id;
    renderConversation();
    return conversation;
}

async function loadConversation(conversationId) {
    const response = await apiFetch(`/api/chat/conversations/${conversationId}`);
    if (!response.ok) {
        throw new Error("Could not load the conversation.");
    }

    const conversation = await response.json();
    upsertConversation(conversation);
    activeConversationId = conversation.id;
    renderConversation();
}

async function loadConversations() {
    const response = await apiFetch("/api/chat/conversations");
    if (!response.ok) {
        throw new Error("Could not load the conversation history.");
    }

    const items = await response.json();
    conversations = items.map((conversation) => ({ ...conversation, messages: [] }));
    sortConversations();

    if (!conversations.length) {
        await createConversation();
        return;
    }

    activeConversationId = conversations[0].id;
    await loadConversation(activeConversationId);
}

async function streamQuestion(question, article) {
    activeRequestController = new AbortController();
    const response = await apiFetch("/api/chat/stream", {
        method: "POST",
        body: JSON.stringify({
            question,
            conversation_id: activeConversationId,
            persona: activePersona,
        }),
        signal: activeRequestController.signal,
    });

    if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload.detail || "Request failed.");
    }

    if (!response.body) {
        throw new Error("Streaming is not supported in this browser.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    const conversation = getActiveConversation();
    const assistantMessage = conversation?.messages[conversation.messages.length - 1];
    let buffer = "";
    let answer = "";

    while (true) {
        const { value, done } = await reader.read();
        if (done) {
            break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
            if (!line.trim()) {
                continue;
            }

            const event = JSON.parse(line);
            if (event.type === "metadata") {
                activeConversationId = event.conversation_id;
                if (assistantMessage) {
                    assistantMessage.persona = activePersona;
                    assistantMessage.sources = event.sources;
                    assistantMessage.context = event.retrieved_documents;
                }
                renderAssistantMetadata(article, {
                    sources: event.sources,
                    context: event.retrieved_documents,
                });
                scrollMessagesToBottom();
                continue;
            }

            if (event.type === "chunk") {
                answer += event.content;
                if (assistantMessage) {
                    assistantMessage.content = answer;
                }
                updateAssistantMessage(article, answer);
                continue;
            }

            if (event.type === "error") {
                throw new Error(event.detail || "Streaming failed.");
            }

            if (event.type === "complete") {
                activeConversationId = event.conversation_id;
                if (assistantMessage) {
                    assistantMessage.content = event.answer;
                }
                updateAssistantMessage(article, event.answer);
                scrollMessagesToBottom();
            }
        }
    }
}

async function startNewChat() {
    activeRequestController?.abort();
    activeRequestController = null;
    statusText.textContent = "";
    questionInput.value = "";
    autoResizeTextarea();
    questionInput.focus();
    await createConversation();
}

async function submitAuth(event) {
    event.preventDefault();

    authStatus.textContent = "";
    authSubmitButton.disabled = true;

    try {
        const response = await apiFetch(`/api/auth/${authMode === "login" ? "login" : "register"}`, {
            method: "POST",
            body: JSON.stringify({
                username: authUsernameInput.value.trim(),
                password: authPasswordInput.value,
            }),
        });

        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.detail || "Authentication failed.");
        }

        setCurrentUser(payload.user);
        showAppShell();
        await loadConversations();
        authForm.reset();
    } catch (error) {
        authStatus.textContent = error.message;
    } finally {
        authSubmitButton.disabled = false;
    }
}

async function restoreSession() {
    try {
        const response = await apiFetch("/api/auth/status");
        const payload = await response.json();

        if (!response.ok || !payload.authenticated) {
            showAuthScreen();
            return;
        }

        setCurrentUser(payload.user);
        showAppShell();
        await loadConversations();
    } catch {
        showAuthScreen();
    }
}

async function handleLogout() {
    activeRequestController?.abort();
    activeRequestController = null;

    await apiFetch("/api/auth/logout", { method: "POST" });
    currentUser = null;
    conversations = [];
    activeConversationId = null;
    messages.innerHTML = "";
    historyList.innerHTML = "";
    statusText.textContent = "";
    showAuthScreen();
}

authForm.addEventListener("submit", submitAuth);
authModeToggle.addEventListener("click", (event) => {
    const target = event.target.closest("[data-auth-mode]");
    if (!target) {
        return;
    }
    setAuthMode(target.dataset.authMode);
});
personaToggleButton.addEventListener("click", (event) => {
    event.stopPropagation();
    const willOpen = personaMenu.classList.contains("hidden");
    personaMenu.classList.toggle("hidden", !willOpen);
    personaMenu.classList.toggle("flex", willOpen);
});
personaOptions.forEach((option) => {
    option.addEventListener("click", (event) => {
        event.stopPropagation();
        setActivePersona(option.dataset.persona);
        closePersonaMenu();
    });
});
logoutButton.addEventListener("click", handleLogout);
document.addEventListener("click", (event) => {
    if (!personaMenu.contains(event.target) && !personaToggleButton.contains(event.target)) {
        closePersonaMenu();
    }
});

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const question = questionInput.value.trim();
    if (!question) {
        statusText.textContent = "Enter a question first.";
        questionInput.focus();
        return;
    }

    if (!getActiveConversation()) {
        await createConversation();
    }

    appendConversationMessage({ role: "user", content: question, sources: [], context: [] });
    questionInput.value = "";
    autoResizeTextarea();
    questionInput.focus();
    sendButton.disabled = true;
    statusText.textContent = "Thinking...";
    const assistantArticle = createAssistantMessage();

    try {
        await streamQuestion(question, assistantArticle);
        await loadConversation(activeConversationId);
        statusText.textContent = "";
        updateHistory();
    } catch (error) {
        updateAssistantMessage(assistantArticle, error.message);
        const conversation = getActiveConversation();
        if (conversation?.messages.length) {
            conversation.messages[conversation.messages.length - 1].content = error.message;
        }
        statusText.textContent = "Request failed.";
    } finally {
        activeRequestController = null;
        sendButton.disabled = false;
    }
});

questionInput.addEventListener("input", autoResizeTextarea);

questionInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        form.requestSubmit();
    }
});

newChatButton.addEventListener("click", startNewChat);

setAuthMode("login");
setActivePersona("accountant");
autoResizeTextarea();
restoreSession();
