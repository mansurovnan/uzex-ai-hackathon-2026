const chatArea = document.getElementById('chatArea');
const chatForm = document.getElementById('chatForm');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const loadingIndicator = document.getElementById('loadingIndicator');

function scrollToBottom() {
    chatArea.scrollTop = chatArea.scrollHeight;
}

function sendSuggestion(text) {
    userInput.value = text;
    handleSend();
}

function renderMarkdown(md) {
    if (!md) return '';

    // Convert Markdown Tables
    const lines = md.split('\n');
    let inTable = false;
    let tableHtml = '';
    let resultLines = [];

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (line.startsWith('|') && line.endsWith('|')) {
            if (!inTable) {
                inTable = true;
                tableHtml = '<div class="chat-table-wrapper"><table class="chat-table">';
                // Header row
                const headers = line.split('|').map(s => s.trim()).filter((s, idx, arr) => idx > 0 && idx < arr.length - 1);
                tableHtml += '<thead><tr>' + headers.map(h => `<th>${h}</th>`).join('') + '</tr></thead><tbody>';
                // Skip next line if it's separator |---|---|
                if (i + 1 < lines.length && lines[i + 1].includes('---')) {
                    i++;
                }
            } else {
                // Table body row
                const cells = line.split('|').map(s => s.trim()).filter((s, idx, arr) => idx > 0 && idx < arr.length - 1);
                tableHtml += '<tr>' + cells.map(c => `<td>${c}</td>`).join('') + '</tr>';
            }
        } else {
            if (inTable) {
                tableHtml += '</tbody></table></div>';
                resultLines.push(tableHtml);
                inTable = false;
                tableHtml = '';
            }
            resultLines.push(line);
        }
    }
    if (inTable) {
        tableHtml += '</tbody></table></div>';
        resultLines.push(tableHtml);
    }

    let parsed = resultLines.join('\n');

    // Bold **text**
    parsed = parsed.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Inline code `code`
    parsed = parsed.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Bullet points
    parsed = parsed.replace(/^- (.*$)/gim, '<li>$1</li>');
    parsed = parsed.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

    // Line breaks
    parsed = parsed.replace(/\n\n/g, '<p></p>');
    parsed = parsed.replace(/\n/g, '<br>');

    return parsed;
}

function appendMessage(sender, content, sql = null, isError = false) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender} ${isError ? 'error' : ''}`;

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    avatar.textContent = sender === 'user' ? 'SIZ' : 'AI';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'msg-content';

    if (sender === 'user') {
        contentDiv.textContent = content;
    } else {
        contentDiv.innerHTML = renderMarkdown(content);

        // Add SQL transparency details if available
        if (sql && !isError) {
            const sqlDetails = document.createElement('details');
            sqlDetails.className = 'sql-accordion';
            sqlDetails.innerHTML = `
                <summary>🔍 Bajarilgan SQL So'rovi / Исполненный SQL</summary>
                <pre><code>${sql}</code></pre>
            `;
            contentDiv.appendChild(sqlDetails);
        }
    }

    msgDiv.appendChild(avatar);
    msgDiv.appendChild(contentDiv);
    chatArea.appendChild(msgDiv);
    scrollToBottom();
}

const sessionId = 'session_' + Math.random().toString(36).substr(2, 9);

async function handleSend(e) {
    if (e) e.preventDefault();

    const query = userInput.value.trim();
    if (!query) return;

    // Display user message
    appendMessage('user', query);
    userInput.value = '';

    // Show loading
    loadingIndicator.style.display = 'flex';
    sendBtn.disabled = true;
    userInput.disabled = true;
    scrollToBottom();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: query, session_id: sessionId })
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `Server xatosi: ${response.status}`);
        }

        const data = await response.json();
        appendMessage('ai', data.answer, data.sql);
    } catch (err) {
        console.error('API Error:', err);
        const friendlyError = "Server bilan aloqada xatolik yuz berdi. Iltimos, server ishga tushirilganligini tekshiring yoki savolni qayta yuboring.\n(Ошибка соединения с сервером. Пожалуйста, повторите запрос.)";
        appendMessage('ai', friendlyError, null, true);
    } finally {
        loadingIndicator.style.display = 'none';
        sendBtn.disabled = false;
        userInput.disabled = false;
        userInput.focus();
        scrollToBottom();
    }
}
