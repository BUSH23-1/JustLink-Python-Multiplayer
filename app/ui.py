"""Web UI for Automated Multi-Platform Posting System (LinkedIn, Telegram, Discord)."""

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>✨ Social Blast Studio</title>
  <style>
    :root {
      --primary: #6366f1;
      --accent: #ec4899;
      --bg: #f0f4ff;
      --card: #ffffff;
      --text: #1e293b;
      --muted: #64748b;
      --border: #e2e8f0;
      --success: #10b981;
      --danger: #ef4444;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
    body { background: linear-gradient(135deg,#f0f4ff 0%,#fdf2f8 50%,#f5f3ff 100%); min-height: 100vh; padding: 30px 15px; display: flex; flex-direction: column; align-items: center; color: var(--text); }
    .container { width: 100%; max-width: 860px; }

    .header { text-align: center; margin-bottom: 28px; }
    .pill { display: inline-flex; align-items: center; gap: 6px; background: white; color: var(--primary); padding: 6px 14px; border-radius: 9999px; font-size: .85rem; font-weight: 600; box-shadow: 0 1px 2px rgba(0,0,0,.05); margin-bottom: 12px; border: 1px solid #e0e7ff; }
    .title { font-size: 2.3rem; font-weight: 800; background: linear-gradient(135deg,#4f46e5,#ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 8px; }
    .subtitle { color: var(--muted); font-size: 1.05rem; }

    .card { background: white; border-radius: 24px; padding: 32px; box-shadow: 0 20px 25px -5px rgba(99,102,241,.15),0 10px 10px -5px rgba(236,72,153,.08); border: 1px solid rgba(255,255,255,.8); margin-bottom: 24px; }
    .field-label { display: flex; justify-content: space-between; align-items: center; font-weight: 700; font-size: 1rem; margin-bottom: 8px; color: #334155; }
    .char { font-size: .85rem; font-weight: 600; color: var(--muted); }
    .char.warn { color: #f59e0b; } .char.danger { color: var(--danger); }
    textarea { width: 100%; min-height: 110px; padding: 16px; border-radius: 16px; border: 2px solid var(--border); background: #f8fafc; font-size: 1rem; color: var(--text); resize: vertical; outline: none; transition: .2s; line-height: 1.5; }
    textarea:focus { border-color: var(--primary); background: #fff; box-shadow: 0 0 0 4px rgba(99,102,241,.15); }

    .quick { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; align-items: center; }
    .quick-label { font-size: .8rem; color: var(--muted); font-weight: 600; text-transform: uppercase; letter-spacing: .5px; }
    .pill-btn { background: #f1f5f9; border: 1px solid #e2e8f0; padding: 6px 12px; border-radius: 9999px; font-size: .82rem; font-weight: 500; color: #475569; cursor: pointer; transition: .15s; }
    .pill-btn:hover { background: #e2e8f0; color: #1e293b; transform: translateY(-1px); }

    .submit-btn { width: 100%; background: linear-gradient(135deg,#6366f1,#ec4899); color: white; border: none; padding: 16px 24px; border-radius: 16px; font-size: 1.1rem; font-weight: 700; cursor: pointer; display: flex; justify-content: center; align-items: center; gap: 10px; box-shadow: 0 8px 20px -4px rgba(99,102,241,.4); transition: .2s; }
    .submit-btn:hover { opacity: .95; transform: translateY(-2px); }
    .submit-btn:disabled { background: #cbd5e1; cursor: not-allowed; transform: none; box-shadow: none; }
    .spinner { width: 22px; height: 22px; border: 3px solid rgba(255,255,255,.3); border-radius: 50%; border-top-color: white; animation: spin .8s ease-in-out infinite; display: none; }
    @keyframes spin { to { transform: rotate(360deg); } }

    .platforms-grid { display: grid; grid-template-columns: repeat(auto-fit,minmax(230px,1fr)); gap: 16px; margin-top: 24px; }
    .platform-card { background: #f8fafc; border: 1px solid var(--border); border-radius: 16px; padding: 18px; display: flex; flex-direction: column; gap: 8px; transition: .2s; }
    .platform-card:hover { transform: translateY(-2px); box-shadow: 0 4px 6px rgba(0,0,0,.07); }

    .platform-header { display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 1rem; }
    .platform-logo { width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; border-radius: 6px; flex-shrink: 0; }
    /* LinkedIn blue */
    .logo-linkedin { background: #0077b5; }
    /* Telegram blue */
    .logo-telegram { background: #2AABEE; }
    /* Discord blurple */
    .logo-discord { background: #5865F2; }

    .status-badge { display: inline-block; padding: 4px 8px; border-radius: 6px; font-size: .75rem; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; }
    .status-ready   { background: #e2e8f0; color: #475569; }
    .status-posting { background: #fef3c7; color: #d97706; }
    .status-success { background: #dcfce7; color: #15803d; }
    .status-failure { background: #fee2e2; color: #b91c1c; }

    .result-info { font-size: .8rem; color: var(--muted); line-height: 1.4; }
    .result-link { color: var(--primary); text-decoration: none; font-weight: 600; display: inline-flex; align-items: center; gap: 4px; margin-top: 6px; }
    .result-link:hover { text-decoration: underline; }

    .footer { text-align: center; color: var(--muted); font-size: .88rem; margin-top: 10px; }
    .footer a { color: var(--primary); text-decoration: none; font-weight: 600; }

    .toast { position: fixed; bottom: 20px; right: 20px; background: white; border-radius: 12px; padding: 14px 20px; box-shadow: 0 10px 15px -3px rgba(0,0,0,.1); border-left: 5px solid var(--primary); display: none; animation: slideIn .3s ease; z-index: 100; font-size: .9rem; font-weight: 500; }
    @keyframes slideIn { from { transform: translateY(100%); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
  </style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="pill">✨ Multi-Platform Poster 1.0</div>
    <h1 class="title">Social Blast Studio</h1>
    <p class="subtitle">Write one message with your link. We publish it to all 3 platforms simultaneously.</p>
  </div>

  <div class="card">
    <div class="field-label">
      <span>💬 Message & Call-To-Action Link</span>
      <span class="char" id="charCount">0 / 200</span>
    </div>
    <textarea id="messageInput" maxlength="250" placeholder="Type your message with one link! E.g. Check out our latest platform! https://example.com">Check out our latest business platform! https://example.com</textarea>

    <div class="quick" style="margin-top:12px;">
      <span class="quick-label">Quick Try:</span>
      <button class="pill-btn" onclick="fill('telegram')">📲 Telegram Link</button>
      <button class="pill-btn" onclick="fill('business')">🚀 Business Link</button>
      <button class="pill-btn" onclick="fill('clear')">🧹 Clear</button>
    </div>

    <button class="submit-btn" id="postBtn" onclick="sendPost()">
      <span class="spinner" id="spinner"></span>
      <span id="btnText">🚀 Publish to All 3 Platforms</span>
    </button>

    <div class="platforms-grid">

      <!-- LinkedIn -->
      <div class="platform-card">
        <div class="platform-header">
          <div class="platform-logo logo-linkedin">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="white" xmlns="http://www.w3.org/2000/svg">
              <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
            </svg>
          </div>
          <span>LinkedIn</span>
        </div>
        <span class="status-badge status-ready" id="badge-LinkedIn">Ready</span>
        <div class="result-info" id="info-LinkedIn">REST Posts API (OAuth 2.0)</div>
      </div>

      <!-- Telegram -->
      <div class="platform-card">
        <div class="platform-header">
          <div class="platform-logo logo-telegram">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="white" xmlns="http://www.w3.org/2000/svg">
              <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
            </svg>
          </div>
          <span>Telegram</span>
        </div>
        <span class="status-badge status-ready" id="badge-Telegram">Ready</span>
        <div class="result-info" id="info-Telegram">Bot API sendMessage</div>
      </div>

      <!-- Discord -->
      <div class="platform-card">
        <div class="platform-header">
          <div class="platform-logo logo-discord">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="white" xmlns="http://www.w3.org/2000/svg">
              <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057.1 18.08.11 18.1.129 18.11a19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/>
            </svg>
          </div>
          <span>Discord</span>
        </div>
        <span class="status-badge status-ready" id="badge-Discord">Ready</span>
        <div class="result-info" id="info-Discord">Webhook API</div>
      </div>

    </div>
  </div>

  <div class="footer">
    Swagger Docs: <a href="/docs" target="_blank">/docs</a> &nbsp;•&nbsp;
    Health: <a href="/health" target="_blank">/health</a> &nbsp;•&nbsp;
    Config: <code>.env</code>
  </div>
</div>
<div class="toast" id="toast"></div>

<script>
  const input = document.getElementById('messageInput');
  const charCount = document.getElementById('charCount');
  const postBtn = document.getElementById('postBtn');
  const spinner = document.getElementById('spinner');
  const btnText = document.getElementById('btnText');
  const toast = document.getElementById('toast');
  const platforms = ['LinkedIn', 'Telegram', 'Discord'];

  const examples = {
    telegram: 'Join our official community today! https://t.me/bushconnect?utm_source=chatgpt.com',
    business: 'Check out our latest business platform! https://example.com',
    clear: ''
  };

  function fill(type) {
    input.value = examples[type] || '';
    updateCount();
    showToast('Example loaded!');
  }

  function updateCount() {
    const len = input.value.length;
    charCount.textContent = `${len} / 200`;
    charCount.className = 'char' + (len > 200 ? ' danger' : len > 170 ? ' warn' : '');
  }
  input.addEventListener('input', updateCount);
  updateCount();

  function showToast(msg, isError = false) {
    toast.textContent = msg;
    toast.style.borderLeftColor = isError ? '#ef4444' : '#6366f1';
    toast.style.display = 'block';
    setTimeout(() => { toast.style.display = 'none'; }, 3500);
  }

  async function sendPost() {
    const text = input.value.trim();
    if (!text) { showToast('Please enter a message!', true); return; }

    postBtn.disabled = true;
    spinner.style.display = 'inline-block';
    btnText.textContent = 'Broadcasting...';
    platforms.forEach(p => {
      document.getElementById(`badge-${p}`).className = 'status-badge status-posting';
      document.getElementById(`badge-${p}`).textContent = 'Posting...';
      document.getElementById(`info-${p}`).textContent = 'Sending request...';
    });

    try {
      const r = await fetch('/posting', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      });
      const data = await r.json();

      if (r.status === 422) {
        const msg = data.detail ? data.detail.map(d => d.msg).join(', ') : 'Validation error';
        showToast(msg, true);
        platforms.forEach(p => {
          document.getElementById(`badge-${p}`).className = 'status-badge status-failure';
          document.getElementById(`badge-${p}`).textContent = 'Invalid Input';
          document.getElementById(`info-${p}`).textContent = msg;
        });
        return;
      }

      (data.results || []).forEach(res => {
        const badge = document.getElementById(`badge-${res.platform}`);
        const info = document.getElementById(`info-${res.platform}`);
        if (!badge) return;
        if (res.status === 'success') {
          badge.className = 'status-badge status-success';
          badge.textContent = 'Success';
          let html = `<div style="color:#10b981;font-weight:600;margin-top:3px;">Published at ${res.time || ''}</div>`;
          if (res.posted_url) html += `<a href="${res.posted_url}" target="_blank" class="result-link">View Post ↗</a>`;
          info.innerHTML = html;
        } else {
          badge.className = 'status-badge status-failure';
          badge.textContent = 'Failed';
          info.innerHTML = `<div style="color:#ef4444;font-size:.78rem;">${res.error || 'Failed'}</div>`;
        }
      });

      showToast(data.success ? '🎉 All platforms published!' : '⚠️ Some platforms failed. Check cards.', !data.success);
    } catch (e) {
      showToast('Network error: ' + e.message, true);
    } finally {
      postBtn.disabled = false;
      spinner.style.display = 'none';
      btnText.textContent = '🚀 Publish to All 3 Platforms';
    }
  }
</script>
</body>
</html>
"""
