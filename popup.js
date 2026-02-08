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
  avatarSelect: document.getElementById('avatarSelect'),
  voiceSelect: document.getElementById('voiceSelect'),
  darkModeToggle: document.getElementById('darkModeToggle'),
  generateBtn: document.getElementById('generateBtn'),
  cancelBtn: document.getElementById('cancelBtn'),
  loader: document.getElementById('loader'),
  statusText: document.getElementById('statusText'),
  errorText: document.getElementById('errorText'),
  previewVideo: document.getElementById('previewVideo'),
  downloadVideoBtn: document.getElementById('downloadVideoBtn'),
  durationEstimate: document.getElementById('durationEstimate'),
};

let currentVideoUrl = null;
let currentJobId = null;
let avatarsList = [];
let voicesList = [];

const STORAGE_KEYS = {
  UI_STATE: 'uiState',
  SELECTED_TEXT: 'selectedText',
  AVATAR_ID: 'avatarId',
  VOICE_ID: 'voiceId'
};

init();

async function init() {
  attachEventListeners();
  await restoreUiState();
  await loadAvatarsAndVoices();
  loadSelectedText();
  updateDurationEstimate();

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
        updateDurationEstimate();
      }
    }
  });
}

function attachEventListeners() {
  elements.inputText.addEventListener('input', () => {
    updateCharCount();
    updateDurationEstimate();
    clearError();
  });
  
  elements.avatarSelect.addEventListener('change', persistUiState);
  elements.voiceSelect.addEventListener('change', persistUiState);
  
  elements.cancelBtn.addEventListener('click', handleCancel);

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
  const stored = await chrome.storage.local.get([
    STORAGE_KEYS.UI_STATE,
    STORAGE_KEYS.AVATAR_ID,
    STORAGE_KEYS.VOICE_ID
  ]);
  const state = stored[STORAGE_KEYS.UI_STATE] || {};

  if (typeof state.darkMode === 'boolean') {
    elements.darkModeToggle.checked = state.darkMode;
    toggleDarkMode(state.darkMode);
  }
  if (state.style) {
    elements.styleSelect.value = state.style;
  }
  if (stored[STORAGE_KEYS.AVATAR_ID]) {
    // Will be set after avatars load
  }
  if (stored[STORAGE_KEYS.VOICE_ID]) {
    // Will be set after voices load
  }
}

async function loadAvatarsAndVoices() {
  try {
    // Load avatars
    const avatarsResponse = await chrome.runtime.sendMessage({ type: 'GET_AVATARS' });
    if (avatarsResponse?.success && avatarsResponse.avatars) {
      avatarsList = avatarsResponse.avatars;
      populateAvatarSelect(avatarsResponse.avatars);
    }
    
    // Load voices
    const voicesResponse = await chrome.runtime.sendMessage({ type: 'GET_VOICES' });
    if (voicesResponse?.success && voicesResponse.voices) {
      voicesList = voicesResponse.voices;
      populateVoiceSelect(voicesResponse.voices);
    }
  } catch (err) {
    console.error('Failed to load avatars/voices:', err);
    // Continue without them - system will auto-select
  }
}

function populateAvatarSelect(avatars) {
  const select = elements.avatarSelect;
  // Keep the "Auto-select" option
  const autoOption = select.options[0];
  select.innerHTML = '';
  select.appendChild(autoOption);
  
  avatars.forEach(avatar => {
    const option = document.createElement('option');
    option.value = avatar.avatar_id;
    option.textContent = avatar.name || avatar.avatar_id;
    select.appendChild(option);
  });
  
  // Restore saved preference
  chrome.storage.local.get(STORAGE_KEYS.AVATAR_ID).then(stored => {
    if (stored[STORAGE_KEYS.AVATAR_ID]) {
      select.value = stored[STORAGE_KEYS.AVATAR_ID];
    }
  });
}

function populateVoiceSelect(voices) {
  const select = elements.voiceSelect;
  // Keep the "Use default" option
  const defaultOption = select.options[0];
  select.innerHTML = '';
  select.appendChild(defaultOption);
  
  // Show first 20 voices to avoid overwhelming UI
  voices.slice(0, 20).forEach(voice => {
    const option = document.createElement('option');
    option.value = voice.voice_id;
    const label = voice.name || voice.voice_id;
    const lang = voice.language ? ` (${voice.language})` : '';
    option.textContent = `${label}${lang}`;
    select.appendChild(option);
  });
  
  // Restore saved preference
  chrome.storage.local.get(STORAGE_KEYS.VOICE_ID).then(stored => {
    if (stored[STORAGE_KEYS.VOICE_ID]) {
      select.value = stored[STORAGE_KEYS.VOICE_ID];
    }
  });
}

function updateDurationEstimate() {
  const text = elements.inputText.value.trim();
  if (!text) {
    elements.durationEstimate.classList.add('hidden');
    return;
  }
  
  // Rough estimate: ~150 words per minute, ~2.5 words per second
  const wordCount = text.split(/\s+/).filter(w => w.length > 0).length;
  const estimatedSeconds = Math.ceil((wordCount / 150) * 60);
  const minutes = Math.floor(estimatedSeconds / 60);
  const seconds = estimatedSeconds % 60;
  
  let estimateText = 'Estimated duration: ';
  if (minutes > 0) {
    estimateText += `${minutes}m ${seconds}s`;
  } else {
    estimateText += `${seconds}s`;
  }
  
  elements.durationEstimate.textContent = estimateText;
  elements.durationEstimate.classList.remove('hidden');
}

function handleCancel() {
  if (currentJobId) {
    setStatus('Cancelling...', true);
    // Note: We can't actually cancel HeyGen jobs, but we can stop polling
    currentJobId = null;
    elements.generateBtn.disabled = false;
    elements.cancelBtn.classList.add('hidden');
    setStatus('Cancelled.', false);
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
  const avatarId = elements.avatarSelect.value || null;
  const voiceId = elements.voiceSelect.value || null;

  elements.generateBtn.disabled = true;
  elements.cancelBtn.classList.remove('hidden');
  setStatus('Sending to Groq AI...', true);

  let completed = false;

  try {
    const response = await chrome.runtime.sendMessage({
      type: 'GENERATE_VIDEO_REQUEST',
      payload: {
        text: rawText,
        style,
        avatar_id: avatarId,
        voice_id: voiceId
      }
    });

    if (!response?.success) {
      showError(response?.message || 'Failed to start video generation.');
      setStatus('Generation failed.', false);
      elements.generateBtn.disabled = false;
      return;
    }

    if (response.jobId) {
      currentJobId = response.jobId;
      // Backend mode - wait for WebSocket/polling updates
      completed = await handleBackendGeneration(response.jobId, response.websocket_available);
    } else {
      throw new Error('Invalid response from backend');
    }

  } catch (err) {
    console.error('Generate error', err);
    showError('Unexpected error while generating video.');
    setStatus('Generation failed.', false);
  } finally {
    elements.generateBtn.disabled = false;
    if (completed || !currentJobId) {
      elements.cancelBtn.classList.add('hidden');
    }
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
        currentJobId = null;
        elements.cancelBtn.classList.add('hidden');
        // Immediately fetch the final result
        await fetchFinalResult(jobId);
      } else if (status === 'error' || status === 'failed') {
        currentJobId = null;
        elements.cancelBtn.classList.add('hidden');
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
  
  return completed;
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
  await chrome.storage.local.set({ 
    [STORAGE_KEYS.UI_STATE]: state,
    [STORAGE_KEYS.AVATAR_ID]: elements.avatarSelect.value || null,
    [STORAGE_KEYS.VOICE_ID]: elements.voiceSelect.value || null
  });
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
