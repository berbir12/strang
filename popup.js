// popup.js
// Handles popup UI interactions:
// - Loads last selection (from context menu or content script)
// - Sends GENERATE_VIDEO_REQUEST to background
// - Receives progress updates
// - Calls videoRenderer to compose a preview video
// - Exposes download options for video and SRT

import { renderExplainerVideo } from './videoRenderer.js';

const MAX_TEXT_LENGTH = 3000;

const elements = {
  root: document.querySelector('.strang-root'),
  inputText: document.getElementById('inputText'),
  charCount: document.getElementById('charCount'),
  refreshSelectionBtn: document.getElementById('refreshSelectionBtn'),
  styleSelect: document.getElementById('styleSelect'),
  durationSelect: document.getElementById('durationSelect'),
  accentSelect: document.getElementById('accentSelect'),
  darkModeToggle: document.getElementById('darkModeToggle'),
  generateBtn: document.getElementById('generateBtn'),
  loader: document.getElementById('loader'),
  statusText: document.getElementById('statusText'),
  errorText: document.getElementById('errorText'),
  previewVideo: document.getElementById('previewVideo'),
  speedSelect: document.getElementById('speedSelect'),
  downloadVideoBtn: document.getElementById('downloadVideoBtn'),
  downloadSrtBtn: document.getElementById('downloadSrtBtn')
};

let currentVideoBlob = null;
let currentVideoUrl = null;
let currentSrt = '';
let currentPlan = null;

const STORAGE_KEYS = {
  UI_STATE: 'uiState',
  LAST_SELECTION: 'lastSelection',
  LAST_PLAN: 'lastPlan'
};

init();

function init() {
  attachEventListeners();
  restoreUiState().then(() => {
    loadInitialSelection();
    loadLastPlan();
  });

  chrome.runtime.onMessage.addListener((message) => {
    if (message.type === 'VIDEO_PROGRESS' && message.payload) {
      const { step, status, message: msg } = message.payload;
      handleProgress(step, status, msg);
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

  elements.speedSelect.addEventListener('change', () => {
    if (elements.previewVideo) {
      const rate = parseFloat(elements.speedSelect.value || '1');
      elements.previewVideo.playbackRate = isNaN(rate) ? 1 : rate;
    }
  });

  elements.darkModeToggle.addEventListener('change', () => {
    const isDark = elements.darkModeToggle.checked;
    toggleDarkMode(isDark);
    persistUiState();
  });

  elements.downloadVideoBtn.addEventListener('click', () => {
    if (!currentVideoBlob && !currentVideoUrl) return;
    const url = currentVideoUrl || URL.createObjectURL(currentVideoBlob);
    const filename = currentVideoUrl ? 'strang-explainer.mp4' : 'strang-explainer.webm';
    triggerDownload(url, filename);
  });

  elements.downloadSrtBtn.addEventListener('click', () => {
    if (!currentSrt) return;
    const blob = new Blob([currentSrt], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    triggerDownload(url, 'strang-explainer.srt');
  });

  elements.styleSelect.addEventListener('change', persistUiState);
  elements.durationSelect.addEventListener('change', persistUiState);
  elements.accentSelect.addEventListener('change', persistUiState);
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
  if (state.duration) {
    elements.durationSelect.value = String(state.duration);
  }
  if (state.voiceAccent) {
    elements.accentSelect.value = state.voiceAccent;
  }
}

async function loadInitialSelection() {
  const response = await chrome.runtime.sendMessage({ type: 'GET_LAST_SELECTION' });
  if (response?.success && response.lastSelection?.text) {
    elements.inputText.value = response.lastSelection.text;
    updateCharCount();
    setStatus('Loaded last selection.', false);
  } else {
    setStatus('Waiting for input...', false);
  }
}

async function loadLastPlan() {
  const stored = await chrome.storage.local.get(STORAGE_KEYS.LAST_PLAN);
  const plan = stored[STORAGE_KEYS.LAST_PLAN];
  if (plan) {
    currentPlan = plan;
    setStatus('Previous plan available. Regenerate to preview again.', false);
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

  const style = elements.styleSelect.value || 'simple';
  const duration = parseInt(elements.durationSelect.value || '60', 10);
  const voiceAccent = elements.accentSelect.value || 'neutral';
  const includeMochi = true;  // Can make this a toggle in UI later

  elements.generateBtn.disabled = true;
  setStatus('Generating plan...', true);

  try {
    const response = await chrome.runtime.sendMessage({
      type: 'GENERATE_VIDEO_REQUEST',
      payload: {
        text: rawText,
        style,
        duration,
        voiceAccent,
        includeMochi
      }
    });

    if (!response?.success) {
      showError(response?.message || 'Failed to generate explainer video plan.');
      setStatus('Generation failed.', false);
      elements.generateBtn.disabled = false;
      return;
    }

    // Check if backend mode (has jobId) or local mode (has plan)
    if (response.jobId) {
      // Backend mode - poll for progress
      await handleBackendGeneration(response.jobId);
    } else if (response.plan) {
      // Local mode - render locally
      currentPlan = response.plan;
      setStatus('Composing video...', true);
      await composeVideoFromPlan(currentPlan);
      setStatus('Video ready. Preview and download below.', false);
    } else {
      throw new Error('Invalid response from backend');
    }

  } catch (err) {
    console.error('Generate error', err);
    showError('Unexpected error while generating explainer.');
    setStatus('Generation failed.', false);
  } finally {
    elements.generateBtn.disabled = false;
  }
}

async function handleBackendGeneration(jobId) {
  // Poll for job progress until complete
  let completed = false;
  let attempts = 0;
  const MAX_ATTEMPTS = 300;  // 300 * 2s = 10 minutes max

  while (!completed && attempts < MAX_ATTEMPTS) {
    attempts++;

    await new Promise(resolve => setTimeout(resolve, 2000));  // Poll every 2 seconds

    try {
      const progressResponse = await chrome.runtime.sendMessage({
        type: 'POLL_JOB_PROGRESS',
        payload: { jobId }
      });

      if (progressResponse?.success && progressResponse.progress) {
        const { status, progress_percent, message } = progressResponse.progress;
        
        setStatus(`${message} (${progress_percent}%)`, true);

        if (status === 'completed') {
          completed = true;
          break;
        } else if (status === 'failed') {
          showError(progressResponse.progress.error || 'Video generation failed on backend');
          setStatus('Generation failed.', false);
          return;
        }
      }
    } catch (err) {
      console.error('Polling error:', err);
      // Continue polling
    }
  }

  if (!completed) {
    showError('Video generation timed out. Please try again.');
    setStatus('Generation timed out.', false);
    return;
  }

  // Get final result
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
      currentSrt = result.srt_content || '';
      
      elements.previewVideo.src = result.video_url;
      elements.previewVideo.load();
      
      elements.downloadVideoBtn.disabled = false;
      elements.downloadSrtBtn.disabled = !currentSrt;
      
      setStatus('Video ready. Preview and download below.', false);
    } else {
      throw new Error('No video URL in result');
    }

  } catch (err) {
    console.error('Failed to get result:', err);
    showError('Failed to retrieve final video from backend');
    setStatus('Fetch failed.', false);
  }
}

async function composeVideoFromPlan(plan) {
  if (currentVideoUrl) {
    URL.revokeObjectURL(currentVideoUrl);
  }

  const canvas = document.createElement('canvas');
  const isDark = elements.root.classList.contains('strang-dark');
  const { blob, url, srt } = await renderExplainerVideo(canvas, plan, {
    theme: isDark ? 'dark' : 'light'
  });

  currentVideoBlob = blob;
  currentVideoUrl = url;
  currentSrt = srt;

  elements.previewVideo.src = url;
  elements.previewVideo.load();

  elements.downloadVideoBtn.disabled = false;
  elements.downloadSrtBtn.disabled = !srt;
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
    style: elements.styleSelect.value,
    duration: parseInt(elements.durationSelect.value || '60', 10),
    voiceAccent: elements.accentSelect.value
  };
  await chrome.storage.local.set({ [STORAGE_KEYS.UI_STATE]: state });
}

function handleProgress(step, status, message) {
  if (status === 'starting') {
    setStatus(message || `Starting ${step}...`, true);
  } else if (status === 'done') {
    setStatus(message || `${step} complete.`, false);
  } else if (status === 'error') {
    showError(message || `Error during ${step}.`);
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

