const state = {
  token: '',
  user: null,
  entitlement: null,
  tutorSessionId: '',
  tutorStatus: 'idle',
  currentStep: 0,
  minRequiredSteps: 4,
};

const el = {
  tabRegister: document.getElementById('tabRegister'),
  tabLogin: document.getElementById('tabLogin'),
  registerForm: document.getElementById('registerForm'),
  loginForm: document.getElementById('loginForm'),
  coachStartForm: document.getElementById('coachStartForm'),
  coachReplyForm: document.getElementById('coachReplyForm'),
  startButton: document.getElementById('startButton'),
  replyButton: document.getElementById('replyButton'),
  idkButton: document.getElementById('idkButton'),
  replyText: document.getElementById('replyText'),
  userStatus: document.getElementById('userStatus'),
  entitlementText: document.getElementById('entitlementText'),
  apiMode: document.getElementById('apiMode'),
  chatThread: document.getElementById('chatThread'),
  sessionMeta: document.getElementById('sessionMeta'),
  messageBar: document.getElementById('messageBar'),
};

function escapeHtml(input) {
  return input
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function showMessage(message, ok = false) {
  el.messageBar.textContent = message;
  el.messageBar.classList.remove('hidden', 'message--error', 'message--ok');
  el.messageBar.classList.add(ok ? 'message--ok' : 'message--error');
}

function clearMessage() {
  el.messageBar.classList.add('hidden');
  el.messageBar.textContent = '';
  el.messageBar.classList.remove('message--error', 'message--ok');
}

function switchTab(mode) {
  const isRegister = mode === 'register';
  el.registerForm.classList.toggle('hidden', !isRegister);
  el.loginForm.classList.toggle('hidden', isRegister);
  el.tabRegister.classList.toggle('tab--active', isRegister);
  el.tabLogin.classList.toggle('tab--active', !isRegister);
  clearMessage();
}

function entitlementSummary(entitlement) {
  if (!entitlement) return '尚未登入';
  if (entitlement.plan === 'company_student_free') {
    return '公司學生免費方案：可持續使用 AI 解題';
  }

  if (entitlement.is_active) {
    return `一般試用方案：剩餘 ${entitlement.days_left} 天`;
  }

  return `方案不可用：${entitlement.reason}`;
}

function addBubble(role, text) {
  const klass = role === 'user' ? 'bubble--user' : role === 'system' ? 'bubble--system' : 'bubble--assistant';
  const item = document.createElement('div');
  item.className = `bubble ${klass}`;
  item.innerHTML = `<p>${escapeHtml(text).replace(/\n/g, '<br />')}</p>`;
  el.chatThread.appendChild(item);
  el.chatThread.scrollTop = el.chatThread.scrollHeight;
}

function resetChatThread() {
  el.chatThread.innerHTML = '';
  addBubble('assistant', '登入後貼上題目，AI 助教會先一步一步提問，再給完整解析。');
}

function updateSessionMeta() {
  if (!state.tutorSessionId) {
    el.sessionMeta.textContent = '尚未開始引導 session';
    return;
  }

  if (state.tutorStatus === 'active') {
    const remain = Math.max(0, state.minRequiredSteps - state.currentStep + 1);
    el.sessionMeta.textContent = `目前第 ${state.currentStep} 輪（至少 ${state.minRequiredSteps} 輪）；最少還需 ${remain} 輪才會進入詳解階段`;
    return;
  }

  if (state.tutorStatus === 'completed') {
    el.sessionMeta.textContent = `本次引導完成，共 ${state.currentStep} 輪。`;
    return;
  }

  if (state.tutorStatus === 'refused') {
    el.sessionMeta.textContent = '本次 session 已因連續三次不知道而暫停。';
  }
}

function applyTutorButtons() {
  const loggedIn = Boolean(state.token && state.user);
  const activeSession = state.tutorSessionId && state.tutorStatus === 'active';

  el.startButton.disabled = !loggedIn;
  el.startButton.textContent = loggedIn ? '開始引導式解題' : '請先登入';

  el.replyButton.disabled = !activeSession;
  el.idkButton.disabled = !activeSession;

  if (!loggedIn) {
    el.replyButton.textContent = '請先開始引導';
    return;
  }

  if (activeSession) {
    el.replyButton.textContent = `送出第 ${state.currentStep} 輪回答`;
  } else if (state.tutorStatus === 'completed') {
    el.replyButton.textContent = '本次引導已完成';
  } else if (state.tutorStatus === 'refused') {
    el.replyButton.textContent = '請先重新開始引導';
  } else {
    el.replyButton.textContent = '請先開始引導';
  }
}

function applyAuthUI() {
  const loggedIn = Boolean(state.token && state.user);

  el.userStatus.textContent = loggedIn ? `已登入：${state.user.name}` : '未登入';
  el.userStatus.classList.toggle('pill--muted', !loggedIn);
  el.entitlementText.textContent = entitlementSummary(state.entitlement);

  if (!loggedIn) {
    el.apiMode.textContent = '等待登入';
  } else if (!state.entitlement?.is_active) {
    el.apiMode.textContent = '方案不可用';
  } else if (state.tutorStatus === 'active') {
    el.apiMode.textContent = '引導中';
  } else if (state.tutorStatus === 'completed') {
    el.apiMode.textContent = '已完成';
  } else if (state.tutorStatus === 'refused') {
    el.apiMode.textContent = '已暫停';
  } else {
    el.apiMode.textContent = '可開始';
  }

  applyTutorButtons();
  updateSessionMeta();
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || `請求失敗 (${response.status})`);
  }

  return data;
}

function onAuthSuccess(payload) {
  state.token = payload.token;
  state.user = payload.user;
  state.entitlement = payload.entitlement;
  state.tutorSessionId = '';
  state.tutorStatus = 'idle';
  state.currentStep = 0;
  resetChatThread();
  applyAuthUI();
  showMessage('登入成功，請開始你的引導式解題。', true);
}

function judgementText(judgement) {
  if (judgement === 'correct') return '答對（升級）';
  if (judgement === 'incorrect') return '答錯（降階）';
  return '不知道（先補基礎）';
}

el.tabRegister.addEventListener('click', () => switchTab('register'));
el.tabLogin.addEventListener('click', () => switchTab('login'));

el.registerForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  clearMessage();

  const payload = {
    name: document.getElementById('registerName').value.trim(),
    email: document.getElementById('registerEmail').value.trim(),
    password: document.getElementById('registerPassword').value,
    in_company_class: document.getElementById('registerCompany').checked,
  };

  try {
    const data = await request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    onAuthSuccess(data);
  } catch (error) {
    showMessage(error.message);
  }
});

el.loginForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  clearMessage();

  const payload = {
    email: document.getElementById('loginEmail').value.trim(),
    password: document.getElementById('loginPassword').value,
  };

  try {
    const data = await request('/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    onAuthSuccess(data);
  } catch (error) {
    showMessage(error.message);
  }
});

el.coachStartForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  clearMessage();

  if (!state.token) {
    showMessage('請先登入再開始引導');
    return;
  }

  const payload = {
    grade: document.getElementById('questionGrade').value.trim(),
    problem: document.getElementById('questionText').value.trim(),
  };

  if (!payload.problem) {
    showMessage('請先輸入題目');
    return;
  }

  el.startButton.disabled = true;
  el.startButton.textContent = '建立引導流程中...';

  try {
    const data = await request('/coach/start', {
      method: 'POST',
      headers: { Authorization: `Bearer ${state.token}` },
      body: JSON.stringify(payload),
    });

    state.entitlement = data.entitlement;
    state.tutorSessionId = data.session_id;
    state.tutorStatus = data.status;
    state.currentStep = data.step;
    state.minRequiredSteps = data.min_required_steps;

    el.replyText.value = '';
    el.chatThread.innerHTML = '';
    addBubble('system', `題目已建立，開始第 ${data.step} 輪引導（至少 ${data.min_required_steps} 輪）。`);
    addBubble('assistant', data.question);

    applyAuthUI();
    showMessage('引導開始，請先回答助教問題。', true);
  } catch (error) {
    showMessage(error.message);
    applyAuthUI();
  }
});

el.coachReplyForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  clearMessage();

  if (!state.token || !state.tutorSessionId || state.tutorStatus !== 'active') {
    showMessage('請先開始引導 session');
    return;
  }

  const answer = el.replyText.value.trim();
  if (!answer) {
    showMessage('請先輸入你的回答');
    return;
  }

  addBubble('user', answer);
  el.replyText.value = '';

  el.replyButton.disabled = true;
  el.replyButton.textContent = '判斷與出題中...';

  try {
    const data = await request('/coach/reply', {
      method: 'POST',
      headers: { Authorization: `Bearer ${state.token}` },
      body: JSON.stringify({ session_id: state.tutorSessionId, answer }),
    });

    state.entitlement = data.entitlement;
    state.tutorStatus = data.status;
    state.currentStep = data.step;

    addBubble('system', `第 ${data.step} 輪判定：${judgementText(data.judgement)}\n回饋：${data.feedback}`);

    if (data.status === 'active' && data.next_question) {
      addBubble('assistant', data.next_question);
      showMessage(`已進入第 ${data.step} 輪，請繼續思考。`, true);
    } else if (data.status === 'completed') {
      addBubble('assistant', `完整解析：\n${data.final_explanation || '（未提供）'}`);
      showMessage('引導完成，已提供完整解析。', true);
    } else if (data.status === 'refused') {
      addBubble('assistant', data.final_explanation || '連續三次不知道，請先回去思考。');
      showMessage('已暫停解答：請先思考後再回來。');
    }
  } catch (error) {
    showMessage(error.message);
  } finally {
    applyAuthUI();
  }
});

el.idkButton.addEventListener('click', () => {
  if (el.idkButton.disabled) return;
  el.replyText.value = '我不知道';
  el.replyText.focus();
});

resetChatThread();
applyAuthUI();
switchTab('register');
