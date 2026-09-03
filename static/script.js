const ragModel = document.getElementById('ragModel');
const userInput = document.getElementById('userInput');
const chatForm = document.getElementById('chatForm');
const chatWindow = document.getElementById('chatWindow');
const promptButtons = document.querySelectorAll('.prompt-btn');

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
      body: JSON.stringify({ message: query, model }),
    });

    const data = await response.json();

    if (!response.ok) {
      addMessage('assistant', data.error || 'Something went wrong.');
      return;
    }

    const safeAnswer = data.answer || 'No answer returned.';
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

chatForm.addEventListener('submit', (event) => {
  event.preventDefault();
  sendRequest();
});

promptButtons.forEach((button) => {
  button.addEventListener('click', () => {
    userInput.value = button.dataset.prompt;
    userInput.focus();
  });
});
