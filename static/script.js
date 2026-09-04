const ragModel = document.getElementById('ragModel');
const userInput = document.getElementById('userInput');
const chatForm = document.getElementById('chatForm');
const chatWindow = document.getElementById('chatWindow');
const promptButtons = document.querySelectorAll('.prompt-btn');
const sessionList = document.getElementById('sessionList');
let activeSessionId = null;

const accountRoot = document.querySelector('.account-actions');
if (window.React && window.ReactDOM && accountRoot) {
  const accountName = accountRoot.querySelector('.status-pill').textContent.trim();
  const AccountActions = () => React.createElement(React.Fragment, null,
    React.createElement('span', { className: 'status-pill' }, accountName),
    React.createElement('button', { id: 'logoutBtn', className: 'logout-btn', type: 'button' }, 'Sign out')
  );
  ReactDOM.createRoot(accountRoot).render(React.createElement(AccountActions));
}

function addMessage(role, text, metadata = null) {
  const messageEl = document.createElement('div');
  messageEl.className = `message ${role}`;

  const label = role === 'user' ? 'You' : 'Assistant';
  const content = document.createElement('div');
  content.innerHTML = `<strong>${label}:</strong><span>${text}</span>`;
  messageEl.appendChild(content);

  if (metadata) {
    const meta = document.createElement('div');
    meta.className = 'meta-box';
    meta.innerHTML = `<strong>Model:</strong> ${metadata.model} | <strong>Confidence:</strong> ${metadata.confidence} | <strong>Sources:</strong> ${metadata.sources}`;
    messageEl.appendChild(meta);
  }

  chatWindow.appendChild(messageEl);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

async function sendRequest() {
  const query = userInput.value.trim();
  if (!query) {
    return;
  }

  const model = ragModel.value;
  addMessage('user', query);
  userInput.value = '';

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message: query, model, session_id: activeSessionId }),
    });

    const data = await response.json();

    if (!response.ok) {
      addMessage('assistant', data.error || 'Something went wrong.');
      return;
    }

    const safeAnswer = data.answer || 'No answer returned.';
    activeSessionId = data.session_id;
    const sourceNames = (data.sources || []).map(item => item.title).slice(0, 3).join(', ') || 'none';
    addMessage('assistant', safeAnswer, {
      model: data.model,
      confidence: data.confidence || 'n/a',
      sources: sourceNames,
    });
  } catch (error) {
    addMessage('assistant', 'The chatbot is unavailable right now. Please try again in a moment.');
  }
}

async function loadSessions() {
  const response = await fetch('/api/sessions');
  if (!response.ok) return;
  const data = await response.json();
  sessionList.innerHTML = '';
  data.sessions.forEach((item) => {
    const row = document.createElement('div');
    row.className = `session-row ${item.id === activeSessionId ? 'active' : ''}`;
    row.innerHTML = `<button class="session-btn" data-id="${item.id}">${item.title}</button><button class="delete-session" data-id="${item.id}" aria-label="Delete session">×</button>`;
    sessionList.appendChild(row);
  });
  document.querySelectorAll('.session-btn').forEach((button) => button.addEventListener('click', () => openSession(button.dataset.id)));
  document.querySelectorAll('.delete-session').forEach((button) => button.addEventListener('click', () => deleteSession(button.dataset.id)));
}

async function openSession(id) {
  const response = await fetch(`/api/sessions/${id}`);
  const data = await response.json();
  if (!response.ok) return;
  activeSessionId = Number(id);
  chatWindow.innerHTML = '';
  data.messages.forEach((message) => addMessage(message.role, message.content));
  loadSessions();
}

async function deleteSession(id) {
  await fetch(`/api/sessions/${id}`, { method: 'DELETE' });
  if (Number(id) === activeSessionId) {
    activeSessionId = null;
    chatWindow.innerHTML = '';
  }
  loadSessions();
}

chatForm.addEventListener('submit', (event) => {
  event.preventDefault();
  sendRequest();
});

document.getElementById('newSessionBtn').addEventListener('click', async () => {
  const response = await fetch('/api/sessions', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({}) });
  const data = await response.json();
  activeSessionId = data.session.id;
  chatWindow.innerHTML = '';
  addMessage('assistant', 'New support session ready. What can I help with?');
  loadSessions();
});

document.getElementById('logoutBtn').addEventListener('click', async () => {
  await fetch('/logout', { method: 'POST' });
  window.location.href = '/login';
});

promptButtons.forEach((button) => {
  button.addEventListener('click', () => {
    userInput.value = button.dataset.prompt;
    userInput.focus();
  });
});

loadSessions();
