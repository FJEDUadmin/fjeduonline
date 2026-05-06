const state = {
  token: '',
  user: null,
  entitlement: null,
};

const el = {
  tabRegister: document.getElementById('tabRegister'),
  tabLogin: document.getElementById('tabLogin'),
  registerForm: document.getElementById('registerForm'),
  loginForm: document.getElementById('loginForm'),
  solveForm: document.getElementById('solveForm'),
  solveButton: document.getElementById('solveButton'),
  userStatus: document.getElementById('userStatus'),
  entitlementText: document.getElementById('entitlementText'),
  apiMode: document.getElementById('apiMode'),
  answerPanel: document.getElementById('answerPanel'),
  messageBar: document.getElementById('messageBar'),
};

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

function applyAuthUI() {
  const loggedIn = Boolean(state.token && state.user);

  el.userStatus.textContent = loggedIn ? `已登入：${state.user.name}` : '未登入';
  el.userStatus.classList.toggle('pill--muted', !loggedIn);

  el.entitlementText.textContent = entitlementSummary(state.entitlement);

  el.solveButton.disabled = !loggedIn;
  el.solveButton.textContent = loggedIn ? '送出題目給 AI 助教' : '請先登入';

  if (!loggedIn) {
    el.apiMode.textContent = '等待登入';
    return;
  }

  if (state.entitlement?.is_active) {
    el.apiMode.textContent = '可解題';
  } else {
    el.apiMode.textContent = '方案不可用';
  }
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
  applyAuthUI();
  showMessage('登入成功，現在可以開始解題。', true);
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

el.solveForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  clearMessage();

  if (!state.token) {
    showMessage('請先登入再解題');
    return;
  }

  const payload = {
    grade: document.getElementById('questionGrade').value.trim(),
    question: document.getElementById('questionText').value.trim(),
  };

  el.solveButton.disabled = true;
  el.solveButton.textContent = 'AI 助教解題中...';

  try {
    const data = await request('/solve', {
      method: 'POST',
      headers: { Authorization: `Bearer ${state.token}` },
      body: JSON.stringify(payload),
    });
    state.entitlement = data.entitlement;
    applyAuthUI();

    el.answerPanel.innerHTML = `<h3>助教回覆</h3><p>${data.answer.replace(/
/g, '<br />')}</p>`;
    showMessage('解題完成。', true);
  } catch (error) {
    showMessage(error.message);
  } finally {
    applyAuthUI();
  }
});

applyAuthUI();
switchTab('register');
