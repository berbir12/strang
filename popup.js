// popup.js
// Handles popup UI interactions:
// - Loads selected text from chrome.storage on init
// - Sends request to /api/process-video endpoint
// - Receives progress updates via WebSocket
// - Displays video preview and download options

const MAX_TEXT_LENGTH = 3000;

const elements = {
  root: document.querySelector('.strang-root'),
  inputText: document.getElementById('inputText'),
  charCount: document.getElementById('charCount'),
  refreshSelectionBtn: document.getElementById('refreshSelectionBtn'),
  styleSelect: document.getElementById('styleSelect'),
  darkModeToggle: document.getElementById('darkModeToggle'),
  generateBtn: document.getElementById('generateBtn'),
  loader: document.getElementById('loader'),
  statusText: document.getElementById('statusText'),
  errorText: document.getElementById('errorText'),
  previewVideo: document.getElementById('previewVideo'),
  downloadVideoBtn: document.getElementById('downloadVideoBtn'),
};

let currentVideoUrl = null;

const STORAGE_KEYS = {
  UI_STATE: 'uiState',
  SELECTED_TEXT: 'selectedText'
};

init();

function init() {
  attachEventListeners();
  restoreUiState().then(() => {
    loadSelectedText();
  });

  // Listen for progress updates from background script
  chrome.runtime.onMessage.addListener((message) => {
    if (message.type === 'VIDEO_PROGRESS' && message.payload) {
      const { step, status, message: msg, progress_percent } = message.payload;
      handleProgress(step, status, msg, progress_percent);
    } else if (message.type === 'SELECTION_UPDATED') {
      const payload = message.payload;
      if (payload?.text && !elements.inputText.value) {
        elements.inputText.value = payload.text;
        updateCharCount();
      }
    }
  });
}

function attachEventListeners() {
  elements.inputText.addEventListener('input', () => {
    updateCharCount();
    clearError();
  });

  elements.refreshSelectionBtn.addEventListener('click', async () => {
    clearError();
    setStatus('Requesting current selection...', true);
    const response = await chrome.runtime.sendMessage({ type: 'REQUEST_ACTIVE_SELECTION' });
    if (!response?.success) {
      showError(response?.message || 'Could not get selection from page.');
      setStatus('Waiting for input...', false);
      return;
    }
    elements.inputText.value = response.lastSelection?.text || '';
    updateCharCount();
    setStatus('Selection loaded from page.', false);
  });

  elements.generateBtn.addEventListener('click', handleGenerateClick);

  elements.darkModeToggle.addEventListener('change', () => {
    const isDark = elements.darkModeToggle.checked;
    toggleDarkMode(isDark);
    persistUiState();
  });

  elements.downloadVideoBtn.addEventListener('click', () => {
    if (!currentVideoUrl) return;
    triggerDownload(currentVideoUrl, 'strang-avatar-video.mp4');
  });

  elements.styleSelect.addEventListener('change', persistUiState);
}

async function restoreUiState() {
  const stored = await chrome.storage.local.get(STORAGE_KEYS.UI_STATE);
  const state = stored[STORAGE_KEYS.UI_STATE] || {};

  if (typeof state.darkMode === 'boolean') {
    elements.darkModeToggle.checked = state.darkMode;
    toggleDarkMode(state.darkMode);
  }
  if (state.style) {
    elements.styleSelect.value = state.style;
  }
}

async function loadSelectedText() {
  // First try to get text from chrome.storage (set by content.js on mouseup)
  const stored = await chrome.storage.local.get(STORAGE_KEYS.SELECTED_TEXT);
  const selectedText = stored[STORAGE_KEYS.SELECTED_TEXT];
  
  if (selectedText && selectedText.trim()) {
    elements.inputText.value = selectedText;
    updateCharCount();
    setStatus('Loaded selected text.', false);
    return;
  }
  
  // Fallback: try to get last selection from background script
  const response = await chrome.runtime.sendMessage({ type: 'GET_LAST_SELECTION' });
  if (response?.success && response.lastSelection?.text) {
    elements.inputText.value = response.lastSelection.text;
    updateCharCount();
    setStatus('Loaded last selection.', false);
  } else {
    setStatus('Waiting for input...', false);
  }
}

function updateCharCount() {
  const len = elements.inputText.value.length;
  elements.charCount.textContent = `${len} / ${MAX_TEXT_LENGTH}`;
  if (len > MAX_TEXT_LENGTH) {
    elements.charCount.style.color = '#b91c1c';
  } else {
    elements.charCount.style.color = '';
  }
}

async function handleGenerateClick() {
  clearError();
  const rawText = elements.inputText.value.trim();
  
  if (!rawText) {
    showError('Please enter or select some text first.');
    return;
  }
  if (rawText.length > MAX_TEXT_LENGTH) {
    showError(`Text is too long. Maximum ${MAX_TEXT_LENGTH} characters.`);
    return;
  }

  const style = elements.styleSelect.value || 'professional';

  elements.generateBtn.disabled = true;
  setStatus('Sending to Groq AI...', true);

  try {
    const response = await chrome.runtime.sendMessage({
      type: 'GENERATE_VIDEO_REQUEST',
      payload: {
        text: rawText,
        style
      }
    });

    if (!response?.success) {
      showError(response?.message || 'Failed to start video generation.');
      setStatus('Generation failed.', false);
      elements.generateBtn.disabled = false;
      return;
    }

    if (response.jobId) {
      // Backend mode - wait for WebSocket/polling updates
      await handleBackendGeneration(response.jobId, response.websocket_available);
    } else {
      throw new Error('Invalid response from backend');
    }

  } catch (err) {
    console.error('Generate error', err);
    showError('Unexpected error while generating video.');
    setStatus('Generation failed.', false);
  } finally {
    elements.generateBtn.disabled = false;
  }
}

async function handleBackendGeneration(jobId, websocketAvailable) {
  let completed = false;
  let lastProgressAt = Date.now();
  let pollIntervalId = null;
  
  // Listen for progress updates from background script
  const progressListener = async (message) => {
    if (message.type === 'VIDEO_PROGRESS' && message.payload) {
      const { status, progress_percent, message: msg } = message.payload;
      lastProgressAt = Date.now();
      
      if (progress_percent !== undefined) {
        setStatus(`${msg} (${progress_percent}%)`, true);
      } else {
        setStatus(msg, true);
      }
      
      if (status === 'completed') {
        completed = true;
        // Immediately fetch the final result
        await fetchFinalResult(jobId);
      } else if (status === 'error' || status === 'failed') {
        showError(msg || 'Video generation failed');
        setStatus('Generation failed.', false);
        completed = true;
      }
    }
  };
  
  chrome.runtime.onMessage.addListener(progressListener);

  const startPolling = () => {
    if (pollIntervalId) return;
    pollIntervalId = setInterval(async () => {
      if (completed) return;
      try {
        const response = await chrome.runtime.sendMessage({
          type: 'POLL_JOB_PROGRESS',
          payload: { jobId }
        });
        if (response?.success && response.progress) {
          const progress = response.progress;
          handleProgress(
            progress.current_step,
            progress.status,
            progress.message,
            progress.progress_percent
          );
        } else if (response?.success && response.progress?.status === 'completed') {
          completed = true;
          await fetchFinalResult(jobId);
        } else if (response?.errorCode === 'POLL_ERROR'
          && response?.message?.includes('HTTP 404')) {
          showError('Job not found. The backend may have restarted.');
          setStatus('Generation failed.', false);
          completed = true;
        }
      } catch (err) {
        console.error('Progress poll failed', err);
      }
    }, 5000);
  };
  
  if (!websocketAvailable) {
    startPolling();
  }
  
  // Wait for completion (no timeout - HeyGen can take 5-10 minutes)
  const startTime = Date.now();
  
  while (!completed) {
    // If WebSocket stops sending updates, start polling
    if (websocketAvailable && Date.now() - lastProgressAt > 8000) {
      startPolling();
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  
  // Clean up listener
  chrome.runtime.onMessage.removeListener(progressListener);
  if (pollIntervalId) {
    clearInterval(pollIntervalId);
  }
}

async function fetchFinalResult(jobId) {
  setStatus('Fetching final video...', true);
  
  try {
    const resultResponse = await chrome.runtime.sendMessage({
      type: 'GET_JOB_RESULT',
      payload: { jobId }
    });

    if (!resultResponse?.success || !resultResponse.result) {
      throw new Error('Failed to retrieve final video');
    }

    const result = resultResponse.result;

    // Set video preview
    if (result.video_url) {
      currentVideoUrl = result.video_url;
      
      elements.previewVideo.src = result.video_url;
      elements.previewVideo.load();
      
      elements.downloadVideoBtn.disabled = false;
      
      setStatus('Video ready! Preview below.', false);
    } else {
      throw new Error('No video URL in result');
    }

  } catch (err) {
    console.error('Failed to get result:', err);
    showError('Failed to retrieve final video');
    setStatus('Fetch failed.', false);
  }
}

function setStatus(text, loading) {
  elements.statusText.textContent = text;
  if (loading) {
    elements.loader.classList.remove('hidden');
  } else {
    elements.loader.classList.add('hidden');
  }
}

function showError(message) {
  elements.errorText.textContent = message;
  elements.errorText.classList.remove('hidden');
}

function clearError() {
  elements.errorText.textContent = '';
  elements.errorText.classList.add('hidden');
}

function toggleDarkMode(enabled) {
  if (enabled) {
    elements.root.classList.add('strang-dark');
    elements.root.classList.remove('strang-light');
  } else {
    elements.root.classList.add('strang-light');
    elements.root.classList.remove('strang-dark');
  }
}

async function persistUiState() {
  const state = {
    darkMode: elements.darkModeToggle.checked,
    style: elements.styleSelect.value
  };
  await chrome.storage.local.set({ [STORAGE_KEYS.UI_STATE]: state });
}

function handleProgress(step, status, message, progress_percent) {
  if (status === 'starting' || status === 'scripting' || status === 'rendering' || status === 'processing') {
    const pct = progress_percent !== undefined ? ` (${progress_percent}%)` : '';
    setStatus(`${message}${pct}`, true);
  } else if (status === 'completed' || status === 'done') {
    // Don't just set status, the progressListener should handle fetching the video
    setStatus(message || 'Video ready!', false);
  } else if (status === 'error' || status === 'failed') {
    showError(message || 'An error occurred.');
    setStatus('An error occurred.', false);
  }
}

function triggerDownload(url, filename) {
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
}
