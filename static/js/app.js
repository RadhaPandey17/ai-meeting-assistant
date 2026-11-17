document.addEventListener('DOMContentLoaded', () => {
  // ── Global State Variables ──
  let selectedFile = null;
  let selectedFsPath = null;
  let activeTranscriptData = null;
  let currentFsPath = "";

  // ── DOM Elements ──
  const navTabs = document.querySelectorAll('.nav-tab');
  const tabPanels = document.querySelectorAll('.tab-panel');
  const statusBadge = document.getElementById('statusBadge');

  // Input Tab Elements
  const ytUrlInput = document.getElementById('ytUrlInput');
  const ytSubmitBtn = document.getElementById('ytSubmitBtn');
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('fileInput');
  const fileSelectedInfo = document.getElementById('fileSelectedInfo');
  const fileName = document.getElementById('fileName');
  const removeFileBtn = document.getElementById('removeFileBtn');
  const openFsModalBtn = document.getElementById('openFsModalBtn');
  const selectedFsPathDisplay = document.getElementById('selectedFsPathDisplay');
  const fsPathText = document.getElementById('fsPathText');
  const languageSelect = document.getElementById('languageSelect');
  const processBtn = document.getElementById('processBtn');

  // Progress Overlay
  const progressContainer = document.getElementById('progressContainer');
  const progressTitle = document.getElementById('progressTitle');
  const progressSubtitle = document.getElementById('progressSubtitle');
  const progressBar = document.getElementById('progressBar');

  // Dashboard Elements
  const meetingTitle = document.getElementById('meetingTitle');
  const metaSource = document.getElementById('metaSource');
  const metaWords = document.getElementById('metaWords');
  const metaLanguage = document.getElementById('metaLanguage');
  const summaryContent = document.getElementById('summaryContent');
  const transcriptContent = document.getElementById('transcriptContent');
  const transcriptSearch = document.getElementById('transcriptSearch');
  const copyTranscriptBtn = document.getElementById('copyTranscriptBtn');
  const exportTxtBtn = document.getElementById('exportTxtBtn');
  const exportJsonBtn = document.getElementById('exportJsonBtn');

  // Chat Elements
  const chatMessages = document.getElementById('chatMessages');
  const chatInput = document.getElementById('chatInput');
  const sendChatBtn = document.getElementById('sendChatBtn');
  const clearMemoryBtn = document.getElementById('clearMemoryBtn');
  const promptChips = document.querySelectorAll('.chip');

  // File System Modal Elements
  const fsModal = document.getElementById('fsModal');
  const closeFsModalBtn = document.getElementById('closeFsModalBtn');
  const cancelFsBtn = document.getElementById('cancelFsBtn');
  const confirmFsBtn = document.getElementById('confirmFsBtn');
  const currentPathText = document.getElementById('currentPathText');
  const fsDirectoryList = document.getElementById('fsDirectoryList');

  // ── 1. Tab Navigation ──
  navTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const targetTabId = tab.getAttribute('data-tab');

      navTabs.forEach(t => t.classList.remove('active'));
      tabPanels.forEach(p => p.classList.remove('active'));

      tab.classList.add('active');
      const targetPanel = document.getElementById(targetTabId);
      if (targetPanel) targetPanel.classList.add('active');
    });
  });

  // ── 2. Drag and Drop File Handling ──
  dropzone.addEventListener('click', (e) => {
    if (e.target.closest('#removeFileBtn')) return;
    fileInput.click();
  });

  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove('dragover');
    });
  });

  dropzone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelected(files[0]);
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      handleFileSelected(e.target.files[0]);
    }
  });

  function handleFileSelected(file) {
    selectedFile = file;
    selectedFsPath = null;
    selectedFsPathDisplay.classList.add('hidden');
    ytUrlInput.value = '';

    fileName.textContent = file.name;
    fileSelectedInfo.classList.remove('hidden');
    dropzone.querySelector('.dropzone-content').classList.add('hidden');
  }

  removeFileBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    selectedFile = null;
    fileInput.value = '';
    fileSelectedInfo.classList.add('hidden');
    dropzone.querySelector('.dropzone-content').classList.remove('hidden');
  });

  // ── 3. Server File System Browser Modal ──
  openFsModalBtn.addEventListener('click', () => {
    fsModal.classList.remove('hidden');
    loadFileSystemPath('');
  });

  closeFsModalBtn.addEventListener('click', () => fsModal.classList.add('hidden'));
  cancelFsBtn.addEventListener('click', () => fsModal.classList.add('hidden'));

  async function loadFileSystemPath(dirPath) {
    fsDirectoryList.innerHTML = '<div class="loading-spinner-sm">Loading directory contents...</div>';
    try {
      const url = dirPath ? `/api/filesystem?path=${encodeURIComponent(dirPath)}` : '/api/filesystem';
      const res = await fetch(url);
      const data = await res.json();

      if (!res.ok) throw new Error(data.detail || 'Failed to fetch directory');

      currentFsPath = data.current_path;
      currentPathText.textContent = currentFsPath;
      renderFsItems(data.parent_path, data.items);
    } catch (err) {
      fsDirectoryList.innerHTML = `<div class="error-msg">Error: ${err.message}</div>`;
    }
  }

  function renderFsItems(parentPath, items) {
    fsDirectoryList.innerHTML = '';
    confirmFsBtn.disabled = true;

    // Up directory item if parent exists
    if (parentPath !== null) {
      const parentItem = document.createElement('div');
      parentItem.className = 'fs-item';
      parentItem.innerHTML = `
        <div class="fs-item-name">
          <i class="fa-solid fa-folder-open" style="color:#f59e0b"></i>
          <span>.. (Up Directory)</span>
        </div>
      `;
      parentItem.addEventListener('click', () => loadFileSystemPath(parentPath));
      fsDirectoryList.appendChild(parentItem);
    }

    if (items.length === 0) {
      fsDirectoryList.innerHTML += '<div style="padding:10px; color:#64748b;">Directory is empty</div>';
      return;
    }

    items.forEach(item => {
      const div = document.createElement('div');
      div.className = 'fs-item';
      const iconClass = item.is_dir ? 'fa-folder' : (item.is_document ? 'fa-file-lines' : (item.is_media ? 'fa-file-audio' : 'fa-file'));
      const iconColor = item.is_dir ? '#f59e0b' : (item.is_document ? '#10b981' : (item.is_media ? '#06b6d4' : '#64748b'));

      div.innerHTML = `
        <div class="fs-item-name">
          <i class="fa-solid ${iconClass}" style="color:${iconColor}"></i>
          <span>${item.name}</span>
        </div>
        <span class="badge">${item.is_dir ? 'Folder' : (item.size ? formatBytes(item.size) : 'File')}</span>
      `;

      div.addEventListener('click', () => {
        if (item.is_dir) {
          loadFileSystemPath(item.path);
        } else {
          document.querySelectorAll('.fs-item').forEach(el => el.classList.remove('selected'));
          div.classList.add('selected');
          selectedFsPath = item.path;
          confirmFsBtn.disabled = false;
        }
      });

      fsDirectoryList.appendChild(div);
    });
  }

  confirmFsBtn.addEventListener('click', () => {
    if (selectedFsPath) {
      selectedFile = null;
      fileSelectedInfo.classList.add('hidden');
      dropzone.querySelector('.dropzone-content').classList.remove('hidden');
      ytUrlInput.value = '';

      fsPathText.textContent = selectedFsPath;
      selectedFsPathDisplay.classList.remove('hidden');
      fsModal.classList.add('hidden');
    }
  });

  // ── 4. Main Processing Action ──
  processBtn.addEventListener('click', () => startProcessing());
  ytSubmitBtn.addEventListener('click', () => startProcessing('yt'));

  async function startProcessing(forcedType = null) {
    const lang = languageSelect.value;
    let endpoint = '';
    let formData = new FormData();
    let payloadJson = {};

    const ytUrl = ytUrlInput.value.trim();

    if (forcedType === 'yt' || (ytUrl && !selectedFile && !selectedFsPath)) {
      if (!ytUrl) {
        alert('Please enter a valid YouTube URL');
        return;
      }
      endpoint = '/api/process/yt';
      payloadJson = { url: ytUrl, language: lang };
    } else if (selectedFile) {
      endpoint = '/api/process/upload';
      formData.append('file', selectedFile);
      formData.append('language', lang);
    } else if (selectedFsPath) {
      endpoint = '/api/process/filesystem';
      payloadJson = { path: selectedFsPath, language: lang };
    } else {
      alert('Please provide a YouTube URL, Drag & Drop an audio file, or select a file from the server file system.');
      return;
    }

    const DOC_EXT = /\.(pdf|docx?|md)$/i;
    const srcName = selectedFile ? selectedFile.name : (selectedFsPath || '');
    if (DOC_EXT.test(srcName)) {
      showProgressOverlay('Processing Document...', 'Scanning pages, extracting text, summarizing, and indexing into RAG.');
    } else {
      showProgressOverlay('Processing Media...', 'Extracting audio, transcribing, summarizing, and indexing into RAG.');
    }
    updateStatus('status-processing', 'Processing...');

    try {
      let response;
      if (endpoint === '/api/process/upload') {
        response = await fetch(endpoint, { method: 'POST', body: formData });
      } else {
        response = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payloadJson)
        });
      }

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Processing failed');

      activeTranscriptData = data;
      renderDashboard(data);

      hideProgressOverlay();
      updateStatus('status-ready', 'Indexed & Ready');

      // Switch to Dashboard Tab
      document.getElementById('dashboardTabBtn').click();
    } catch (err) {
      hideProgressOverlay();
      updateStatus('status-ready', 'System Ready');
      alert(`Processing Error: ${err.message}`);
    }
  }

  // ── 5. Render Dashboard & Summary ──
  function renderDashboard(data) {
    meetingTitle.textContent = data.title || 'Untitled Meeting Summary';
    metaSource.innerHTML = `<i class="fa-solid fa-link"></i> Source: ${data.source || 'Uploaded File'}`;
    metaWords.innerHTML = `<i class="fa-solid fa-font"></i> Words: ${data.word_count || 0}`;
    const isDoc = data.source_type === 'document';
    metaLanguage.innerHTML = isDoc
      ? `<i class="fa-solid fa-file-lines"></i> Type: Document`
      : `<i class="fa-solid fa-language"></i> Engine: ${data.language || 'Whisper'}`;
    const tTitle = document.getElementById('transcriptTitle');
    if (tTitle) tTitle.textContent = isDoc ? 'Full Document Text' : 'Full Transcript';

    // Simple markdown formatting replacement for bullet points / bold
    let formattedSummary = (data.summary || '')
      .replace(/\n/g, '<br>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/- (.*?)(<br>|$)/g, '<li>$1</li>');

    if (formattedSummary.includes('<li>')) {
      formattedSummary = `<ul>${formattedSummary}</ul>`;
    }

    summaryContent.innerHTML = formattedSummary || '<p>No summary generated.</p>';
    transcriptContent.textContent = data.transcript || 'No transcript text available.';
  }

  // Search Transcript Filter
  transcriptSearch.addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase();
    if (!activeTranscriptData || !activeTranscriptData.transcript) return;

    if (!query) {
      transcriptContent.textContent = activeTranscriptData.transcript;
      return;
    }

    const text = activeTranscriptData.transcript;
    const lines = text.split('\n');
    const filteredLines = lines.filter(line => line.toLowerCase().includes(query));
    transcriptContent.textContent = filteredLines.join('\n') || 'No matching lines found.';
  });

  // Copy Transcript
  copyTranscriptBtn.addEventListener('click', () => {
    if (!activeTranscriptData || !activeTranscriptData.transcript) return;
    navigator.clipboard.writeText(activeTranscriptData.transcript);
    const originalText = copyTranscriptBtn.innerHTML;
    copyTranscriptBtn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
    setTimeout(() => copyTranscriptBtn.innerHTML = originalText, 2000);
  });

  // Export TXT / JSON
  exportTxtBtn.addEventListener('click', () => {
    if (!activeTranscriptData) return;
    const blob = new Blob([`TITLE: ${activeTranscriptData.title}\n\nSUMMARY:\n${activeTranscriptData.summary}\n\n${activeTranscriptData.source_type === 'document' ? 'FULL DOCUMENT TEXT' : 'FULL TRANSCRIPT'}:\n${activeTranscriptData.transcript}`], { type: 'text/plain' });
    downloadFile(blob, activeTranscriptData.source_type === 'document' ? 'document_summary.txt' : 'meeting_summary.txt');
  });

  exportJsonBtn.addEventListener('click', () => {
    if (!activeTranscriptData) return;
    const blob = new Blob([JSON.stringify(activeTranscriptData, null, 2)], { type: 'application/json' });
    downloadFile(blob, activeTranscriptData.source_type === 'document' ? 'document_data.json' : 'meeting_data.json');
  });

  function downloadFile(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  // ── 6. RAG AI Chat Interface ──
  sendChatBtn.addEventListener('click', () => sendChatMessage());
  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') sendChatMessage();
  });

  promptChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const prompt = chip.getAttribute('data-prompt');
      chatInput.value = prompt;
      sendChatMessage();
    });
  });

  async function sendChatMessage() {
    const question = chatInput.value.trim();
    if (!question) return;

    appendChatMessage('user', question);
    chatInput.value = '';

    const typingBubble = appendChatMessage('assistant', '<i class="fa-solid fa-circle-notch fa-spin"></i> Searching hybrid BM25 + Vector index...');

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Chat query failed');

      typingBubble.querySelector('.message-bubble').innerHTML = formatMarkdownText(data.answer);
      chatMessages.scrollTop = chatMessages.scrollHeight;
    } catch (err) {
      typingBubble.querySelector('.message-bubble').innerHTML = `<span style="color:#ef4444;">Error: ${err.message}</span>`;
    }
  }

  function appendChatMessage(role, content) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message message-${role}`;
    msgDiv.innerHTML = `<div class="message-bubble">${content}</div>`;
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return msgDiv;
  }

  clearMemoryBtn.addEventListener('click', async () => {
    try {
      await fetch('/api/clear-memory', { method: 'POST' });
      chatMessages.innerHTML = `
        <div class="message message-system">
          <div class="message-bubble">🧹 Conversational chat memory reset. You can ask fresh questions now.</div>
        </div>
      `;
    } catch (err) {
      alert('Failed to clear memory');
    }
  });

  // ── Helpers ──
  function showProgressOverlay(title, subtitle) {
    progressTitle.textContent = title;
    progressSubtitle.textContent = subtitle;
    progressBar.style.width = '60%';
    progressContainer.classList.remove('hidden');
  }

  function hideProgressOverlay() {
    progressBar.style.width = '100%';
    setTimeout(() => {
      progressContainer.classList.add('hidden');
      progressBar.style.width = '0%';
    }, 300);
  }

  function updateStatus(statusClass, text) {
    statusBadge.className = `status-badge ${statusClass}`;
    statusBadge.querySelector('.status-text').textContent = text;
  }

  function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  function formatMarkdownText(txt) {
    return txt
      .replace(/\n/g, '<br>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  }
});
