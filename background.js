// background.js (Service Worker)
// - Creates context menu
// - Mediates messaging between content scripts and popup
// - Calls backend API for video generation (or falls back to local mock)
// - Manages basic caching and progress updates

import { generateVideoPlan } from './aiMock.js';

const STORAGE_KEYS = {
  LAST_SELECTION: 'lastSelection',
  LAST_PLAN: 'lastPlan',
  UI_STATE: 'uiState',
  LAST_JOB: 'lastJob'
};

const MAX_TEXT_LENGTH = 3000;

// Backend API URL - configure this based on your deployment
const BACKEND_URL = 'http://localhost:8000';
const USE_BACKEND = true;  // Set to false to use local mock pipeline

// Create context menu for selected text
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'strang-generate-explainer',
    title: 'Generate Explainer Video with Strang',
    contexts: ['selection']
  });
});

// Handle context menu click
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId !== 'strang-generate-explainer') return;

  const text = (info.selectionText || '').trim();
  if (!text) {
    return;
  }

  const safeText = sanitizeText(text);
  const selectionPayload = {
    text: safeText,
    source: 'context-menu',
    url: tab?.url || '',
    timestamp: Date.now()
  };

  chrome.storage.local.set({ [STORAGE_KEYS.LAST_SELECTION]: selectionPayload });

  // Notify any open popup that a new selection is available
  chrome.runtime.sendMessage({
    type: 'SELECTION_UPDATED',
    payload: selectionPayload
  }).catch(() => {
    // Popup might not be open; ignore errors
  });
});

// Main message router
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  (async () => {
    try {
      switch (message.type) {
        case 'GET_LAST_SELECTION':
          await handleGetLastSelection(sendResponse);
          break;
        case 'REQUEST_ACTIVE_SELECTION':
          await handleRequestActiveSelection(sendResponse);
          break;
        case 'GENERATE_VIDEO_REQUEST':
          await handleGenerateVideoRequest(message.payload, sendResponse);
          break;
        case 'POLL_JOB_PROGRESS':
          await handlePollJobProgress(message.payload, sendResponse);
          break;
        case 'GET_JOB_RESULT':
          await handleGetJobResult(message.payload, sendResponse);
          break;
        default:
          // Unknown message type; ignore
          break;
      }
    } catch (err) {
      console.error('Background message handler error', err);
      sendResponse({
        success: false,
        errorCode: 'UNEXPECTED_ERROR',
        message: 'An unexpected error occurred in the background script.'
      });
    }
  })();

  // Indicate async response
  return true;
});

async function handleGetLastSelection(sendResponse) {
  const stored = await chrome.storage.local.get(STORAGE_KEYS.LAST_SELECTION);
  const lastSelection = stored[STORAGE_KEYS.LAST_SELECTION] || null;
  sendResponse({ success: true, lastSelection });
}

async function handleRequestActiveSelection(sendResponse) {
  // Ask the active tab's content script for the latest selection
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) {
    sendResponse({
      success: false,
      errorCode: 'NO_ACTIVE_TAB',
      message: 'No active tab found.'
    });
    return;
  }

  try {
    const response = await chrome.tabs.sendMessage(tab.id, { type: 'GET_SELECTION' });
    const text = sanitizeText((response && response.text) || '');
    if (!text) {
      sendResponse({
        success: false,
        errorCode: 'EMPTY_SELECTION',
        message: 'No text is currently selected on the page.'
      });
      return;
    }

    const selectionPayload = {
      text,
      source: 'content-script',
      url: tab.url || '',
      timestamp: Date.now()
    };
    await chrome.storage.local.set({ [STORAGE_KEYS.LAST_SELECTION]: selectionPayload });

    sendResponse({ success: true, lastSelection: selectionPayload });
  } catch (err) {
    console.error('Error requesting selection from content script', err);
    sendResponse({
      success: false,
      errorCode: 'CONTENT_SCRIPT_COMM_ERROR',
      message: 'Could not communicate with the content script on the active tab.'
    });
  }
}

async function handleGenerateVideoRequest(payload, sendResponse) {
  const { text, style, duration, voiceAccent, includeMochi } = payload || {};
  const cleanedText = sanitizeText(text || '');

  if (!cleanedText) {
    sendResponse({
      success: false,
      errorCode: 'EMPTY_TEXT',
      message: 'Please provide some text to generate an explainer video.'
    });
    return;
  }

  if (cleanedText.length > MAX_TEXT_LENGTH) {
    sendResponse({
      success: false,
      errorCode: 'TEXT_TOO_LONG',
      message: `Selected text is too long. Maximum allowed length is ${MAX_TEXT_LENGTH} characters.`
    });
    return;
  }

  // Basic validation of style/duration
  const safeStyle = style || 'simple';
  const safeDuration = [30, 60, 120].includes(duration) ? duration : 60;
  const safeVoiceAccent = voiceAccent || 'neutral';
  const useMochi = includeMochi !== false;  // Default true

  if (USE_BACKEND) {
    // Use backend API (hybrid Manim + Mochi pipeline)
    await handleBackendGeneration({
      text: cleanedText,
      style: safeStyle,
      duration: safeDuration,
      voiceAccent: safeVoiceAccent,
      includeMochi: useMochi
    }, sendResponse);
  } else {
    // Fallback to local mock pipeline
    await handleLocalGeneration({
      text: cleanedText,
      style: safeStyle,
      duration: safeDuration,
      voiceAccent: safeVoiceAccent
    }, sendResponse);
  }
}

async function handleBackendGeneration(params, sendResponse) {
  const { text, style, duration, voiceAccent, includeMochi } = params;

  broadcastProgress({
    step: 'backend',
    status: 'starting',
    message: 'Sending request to backend...'
  });

  try {
    // Call backend API
    const response = await fetch(`${BACKEND_URL}/generate-video`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        text,
        style,
        duration,
        voice_accent: voiceAccent,
        include_mochi: includeMochi
      })
    });

    if (!response.ok) {
      throw new Error(`Backend error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    const jobId = data.job_id;

    // Store job info
    await chrome.storage.local.set({
      [STORAGE_KEYS.LAST_JOB]: {
        jobId,
        status: 'processing',
        timestamp: Date.now()
      }
    });

    broadcastProgress({
      step: 'backend',
      status: 'submitted',
      message: 'Video generation started. Job ID: ' + jobId
    });

    sendResponse({
      success: true,
      jobId,
      estimated_time: data.estimated_time_seconds,
      message: 'Job submitted. Poll for progress using jobId.'
    });

  } catch (err) {
    console.error('Backend generation error', err);
    broadcastProgress({
      step: 'backend',
      status: 'error',
      message: `Backend failed: ${err.message}`
    });

    sendResponse({
      success: false,
      errorCode: 'BACKEND_ERROR',
      message: `Failed to connect to backend: ${err.message}`
    });
  }
}

async function handleLocalGeneration(params, sendResponse) {
  // Fallback to local mock
  broadcastProgress({
    step: 'pipeline',
    status: 'starting',
    message: 'Starting local AI pipeline...'
  });

  try {
    const plan = await generateVideoPlan(params);

    await chrome.storage.local.set({
      [STORAGE_KEYS.LAST_PLAN]: plan
    });

    broadcastProgress({
      step: 'pipeline',
      status: 'done',
      message: 'AI plan generated.'
    });

    sendResponse({
      success: true,
      plan
    });
  } catch (err) {
    console.error('Error generating video plan', err);
    broadcastProgress({
      step: 'pipeline',
      status: 'error',
      message: 'Failed to generate AI plan.'
    });

    sendResponse({
      success: false,
      errorCode: 'PIPELINE_ERROR',
      message: 'Failed to generate content for the explainer video.'
    });
  }
}

async function handlePollJobProgress(payload, sendResponse) {
  const { jobId } = payload || {};
  if (!jobId) {
    sendResponse({
      success: false,
      errorCode: 'MISSING_JOB_ID',
      message: 'Job ID is required'
    });
    return;
  }

  try {
    const response = await fetch(`${BACKEND_URL}/job/${jobId}/progress`);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const progress = await response.json();

    // Broadcast progress update to popup
    broadcastProgress({
      step: progress.current_step,
      status: progress.status,
      message: progress.message,
      progress_percent: progress.progress_percent
    });

    sendResponse({
      success: true,
      progress
    });
  } catch (err) {
    console.error('Poll job progress error', err);
    sendResponse({
      success: false,
      errorCode: 'POLL_ERROR',
      message: `Failed to poll job progress: ${err.message}`
    });
  }
}

async function handleGetJobResult(payload, sendResponse) {
  const { jobId } = payload || {};
  if (!jobId) {
    sendResponse({
      success: false,
      errorCode: 'MISSING_JOB_ID',
      message: 'Job ID is required'
    });
    return;
  }

  try {
    const response = await fetch(`${BACKEND_URL}/job/${jobId}/result`);
    
    if (response.status === 202) {
      // Still processing
      sendResponse({
        success: false,
        errorCode: 'JOB_PROCESSING',
        message: 'Job is still processing'
      });
      return;
    }

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const result = await response.json();

    // Convert relative URLs to absolute
    if (result.video_url && !result.video_url.startsWith('http')) {
      result.video_url = `${BACKEND_URL}${result.video_url}`;
    }
    if (result.thumbnail_url && !result.thumbnail_url.startsWith('http')) {
      result.thumbnail_url = `${BACKEND_URL}${result.thumbnail_url}`;
    }

    sendResponse({
      success: true,
      result
    });
  } catch (err) {
    console.error('Get job result error', err);
    sendResponse({
      success: false,
      errorCode: 'RESULT_ERROR',
      message: `Failed to get job result: ${err.message}`
    });
  }
}

function sanitizeText(text) {
  if (!text) return '';
  const stripped = text
    // Remove HTML tags if any
    .replace(/<[^>]*>/g, ' ')
    // Normalize whitespace
    .replace(/\s+/g, ' ')
    .trim();
  return stripped;
}

function broadcastProgress({ step, status, message }) {
  chrome.runtime.sendMessage({
    type: 'VIDEO_PROGRESS',
    payload: { step, status, message }
  }).catch(() => {
    // Popup may not be open; safe to ignore
  });
}

