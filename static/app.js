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

const wakingBanner = document.getElementById('wakingBanner');
const wakingText = document.getElementById('wakingText');

function appendMessage(sender, content, sql = null, isError = false, evidence = null) {
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

        // Add Evidence & SQL transparency details if available
        if ((sql || evidence) && !isError) {
            const sqlDetails = document.createElement('details');
            sqlDetails.className = 'sql-accordion';

            let evidenceHtml = '';
            if (evidence) {
                const planEntity = evidence.plan ? evidence.plan.target_entity : 'general';
                const limit = evidence.plan && evidence.plan.ranking_limit ? ` (Limit: ${evidence.plan.ranking_limit})` : '';
                
                const entities = (evidence.resolved_entities || [])
                    .filter(e => e && e.val)
                    .map(e => `<code>${e.type}: ${typeof e.val === 'object' ? JSON.stringify(e.val) : e.val}</code>`)
                    .join(' ') || '<em>Barcha birja</em>';

                const checks = Object.entries(evidence.cross_checks || {})
                    .map(([k, v]) => `<span class="check-badge ${v ? 'pass' : 'fail'}">${v ? '✓' : '✗'} ${k}</span>`)
                    .join(' ');

                const caveats = (evidence.coverage_notes || [])
                    .map(c => `<div class="caveat-badge">⚠️ ${c}</div>`)
                    .join('');

                evidenceHtml = `
                    <div class="evidence-container">
                        <div class="evidence-row"><strong>📌 Reja / План:</strong> <code>${planEntity}${limit}</code> | Qatorlar: <code>${evidence.row_count || 0}</code></div>
                        <div class="evidence-row"><strong>🎯 Aniqlangan subyektlar:</strong> ${entities}</div>
                        <div class="evidence-row"><strong>🔬 Tekshiruvlar (Cross-checks):</strong> ${checks || '<em>Avtomatik tasdiqlangan</em>'}</div>
                        ${caveats}
                    </div>
                `;
            }

            const sqlPre = sql ? `<pre><code>${sql}</code></pre>` : '';

            sqlDetails.innerHTML = `
                <summary>🔍 Tahliliy dalillar va SQL / Аналитические свидетельства и SQL</summary>
                ${evidenceHtml}
                ${sqlPre}
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

function showWakingState(msg) {
    if (wakingBanner) {
        if (msg && wakingText) wakingText.textContent = msg;
        wakingBanner.style.display = 'flex';
    }
}

function hideWakingState() {
    if (wakingBanner) {
        wakingBanner.style.display = 'none';
    }
}

async function pollHealthUntilReady(maxWaitMs = 120000) {
    const startTime = Date.now();
    let delay = 2000;
    while (Date.now() - startTime < maxWaitMs) {
        try {
            const res = await fetch('/api/health');
            if (res.ok) {
                const data = await res.json();
                if (data.ready || data.status === 'healthy') {
                    return true;
                }
            }
        } catch (e) {
            // Server waking, continue waiting
        }
        await new Promise(r => setTimeout(r, delay));
        delay = Math.min(delay * 1.5, 8000);
    }
    return false;
}

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

    // Cold-start timer: if request takes > 3.5s, trigger waking alert
    const coldStartTimer = setTimeout(() => {
        showWakingState("⚡ Server uyqu rejimidan uyg'onmoqda (Render Free). Iltimos, 30-60 soniya kuting... / Сервер выходит из спящего режима...");
    }, 3500);

    try {
        let response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: query, session_id: sessionId })
        });

        clearTimeout(coldStartTimer);

        // If server was cold and returned 502/503/504 gateway waking error
        if (response.status === 502 || response.status === 503 || response.status === 504) {
            showWakingState("⚡ Render Free serveri uyg'onmoqda... Tayyor bo'lgach so'rov avtomatik qayta yuboriladi.");
            const ready = await pollHealthUntilReady(90000);
            if (ready) {
                response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: query, session_id: sessionId })
                });
            }
        }

        hideWakingState();

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `Server xatosi: ${response.status}`);
        }

        const data = await response.json();
        appendMessage('ai', data.answer, data.sql, false, data.evidence);
    } catch (err) {
        clearTimeout(coldStartTimer);
        hideWakingState();
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
