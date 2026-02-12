// background.js (Service Worker)
// - Creates context menu for text selection
// - Handles API calls to Grok + HeyGen backend
// - Manages WebSocket connections for real-time progress
// - Broadcasts progress updates to popup

const STORAGE_KEYS = {
  LAST_SELECTION: 'lastSelection',
  LAST_JOB: 'lastJob',
  UI_STATE: 'uiState'
};

const MAX_TEXT_LENGTH = 3000;

// Backend API URL - configure for your deployment
const BACKEND_URL = 'http://localhost:8000';
const BACKEND_WS_URL = 'ws://localhost:8000';
const USE_WEBSOCKET = true;

// WebSocket management
let activeWebSockets = new Map();

// Create context menu for selected text
chrome.runtime.onInstalled.addListener(() => {
  // Remove all existing context menus to avoid duplicate ID errors
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: 'strang-generate-video',
      title: 'Generate Avatar Video with Strang',
      contexts: ['selection']
    });
  });
});

// Handle context menu click
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId !== 'strang-generate-video') return;

  const text = (info.selectionText || '').trim();
  if (!text) return;

  const safeText = sanitizeText(text);
  const selectionPayload = {
    text: safeText,
    source: 'context-menu',
    url: tab?.url || '',
    timestamp: Date.now()
  };

  chrome.storage.local.set({
    [STORAGE_KEYS.LAST_SELECTION]: selectionPayload,
    selectedText: safeText
  });

  // Notify popup if open
  chrome.runtime.sendMessage({
    type: 'SELECTION_UPDATED',
    payload: selectionPayload
  }).catch(() => { });
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
        case 'GET_AVATARS':
          await handleGetAvatars(sendResponse);
          break;
        case 'GET_VOICES':
          await handleGetVoices(sendResponse);
          break;
        default:
          break;
      }
    } catch (err) {
      console.error('Background message handler error', err);
      sendResponse({
        success: false,
        errorCode: 'UNEXPECTED_ERROR',
        message: 'An unexpected error occurred.'
      });
    }
  })();

  return true; // Async response
});

async function handleGetLastSelection(sendResponse) {
  const stored = await chrome.storage.local.get(STORAGE_KEYS.LAST_SELECTION);
  const lastSelection = stored[STORAGE_KEYS.LAST_SELECTION] || null;
  sendResponse({ success: true, lastSelection });
}

async function handleRequestActiveSelection(sendResponse) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) {
    sendResponse({
      success: false,
      errorCode: 'NO_ACTIVE_TAB',
      message: 'No active tab found.'
    });
    return;
  }

  const tabUrl = tab.url || '';
  if (!tabUrl || /^(chrome|edge|devtools|chrome-extension|about):/i.test(tabUrl)) {
    sendResponse({
      success: false,
      errorCode: 'UNSUPPORTED_PAGE',
      message: 'Cannot access selections on this type of page.'
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
        message: 'No text is currently selected.'
      });
      return;
    }

    const selectionPayload = {
      text,
      source: 'content-script',
      url: tab.url || '',
      timestamp: Date.now()
    };

    await chrome.storage.local.set({
      [STORAGE_KEYS.LAST_SELECTION]: selectionPayload,
      selectedText: text
    });

    sendResponse({ success: true, lastSelection: selectionPayload });
  } catch (err) {
    const message = err?.message || String(err);
    const isMissingReceiver = message.includes('Receiving end does not exist')
      || message.includes('Could not establish connection');

    if (isMissingReceiver) {
      try {
        await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          files: ['content.js']
        });

        const retry = await chrome.tabs.sendMessage(tab.id, { type: 'GET_SELECTION' });
        const text = sanitizeText((retry && retry.text) || '');

        if (!text) {
          sendResponse({
            success: false,
            errorCode: 'EMPTY_SELECTION',
            message: 'No text is currently selected.'
          });
          return;
        }

        const selectionPayload = {
          text,
          source: 'content-script',
          url: tab.url || '',
          timestamp: Date.now()
        };

        await chrome.storage.local.set({
          [STORAGE_KEYS.LAST_SELECTION]: selectionPayload,
          selectedText: text
        });

        sendResponse({ success: true, lastSelection: selectionPayload });
        return;
      } catch (retryErr) {
        console.error('Error requesting selection from content script', retryErr);
      }
    } else {
      console.error('Error requesting selection from content script', err);
    }
    sendResponse({
      success: false,
      errorCode: 'CONTENT_SCRIPT_COMM_ERROR',
      message: 'Could not communicate with content script. Try reloading the page.'
    });
  }
}

async function handleGenerateVideoRequest(payload, sendResponse) {
  const { text, style, avatar_id, voice_id } = payload || {};
  const cleanedText = sanitizeText(text || '');

  if (!cleanedText) {
    sendResponse({
      success: false,
      errorCode: 'EMPTY_TEXT',
      message: 'Please provide some text to generate a video.'
    });
    return;
  }

  if (cleanedText.length > MAX_TEXT_LENGTH) {
    sendResponse({
      success: false,
      errorCode: 'TEXT_TOO_LONG',
      message: `Text too long. Maximum ${MAX_TEXT_LENGTH} characters.`
    });
    return;
  }

  const safeStyle = style || 'professional';

  broadcastProgress({
    step: 'backend',
    status: 'starting',
    message: 'Sending request to backend...'
  });

  try {
    // Build request body
    const requestBody = {
      text: cleanedText,
      style: safeStyle
    };

    // Add optional avatar and voice if provided
    if (avatar_id) {
      requestBody.avatar_id = avatar_id;
    }
    if (voice_id) {
      requestBody.voice_id = voice_id;
    }

    // Call new /api/process-video endpoint
    const response = await fetch(`${BACKEND_URL}/api/process-video`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody)
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
      message: 'Job submitted. Groq is scripting...'
    });

    // Connect WebSocket for real-time updates
    const ws = connectWebSocket(jobId);

    sendResponse({
      success: true,
      jobId,
      estimated_time: data.estimated_time_seconds,
      message: 'Job submitted successfully.',
      websocket_available: !!ws
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

function connectWebSocket(jobId) {
  if (!USE_WEBSOCKET) {
    console.log('[WebSocket] Disabled');
    return null;
  }

  // Clean up existing connection
  if (activeWebSockets.has(jobId)) {
    activeWebSockets.get(jobId).close();
    activeWebSockets.delete(jobId);
  }

  try {
    const ws = new WebSocket(`${BACKEND_WS_URL}/ws/job/${jobId}`);

    ws.onopen = () => {
      console.log(`[WebSocket] Connected to job ${jobId}`);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log(`[WebSocket] Message:`, data);

        if (data.type === 'progress' || data.type === 'connected') {
          broadcastProgress({
            step: data.current_step,
            status: data.status,
            message: data.message,
            progress_percent: data.progress_percent
          });
        } else if (data.type === 'complete') {
          broadcastProgress({
            step: 'completed',
            status: 'completed',
            message: 'Video generation complete!',
            progress_percent: 100
          });
          ws.close();
          activeWebSockets.delete(jobId);
        } else if (data.type === 'error') {
          broadcastProgress({
            step: 'failed',
            status: 'error',
            message: data.error || 'Video generation failed',
            progress_percent: 0
          });
          ws.close();
          activeWebSockets.delete(jobId);
        }
      } catch (err) {
        console.error('[WebSocket] Parse error:', err);
      }
    };

    ws.onerror = (error) => {
      console.error('[WebSocket] Error:', error);
      activeWebSockets.delete(jobId);
    };

    ws.onclose = (event) => {
      console.log(`[WebSocket] Closed: ${event.code}`);
      activeWebSockets.delete(jobId);
    };

    activeWebSockets.set(jobId, ws);

    // Ping to keep alive
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
      } else {
        clearInterval(pingInterval);
      }
    }, 20000);

    return ws;

  } catch (err) {
    console.error('[WebSocket] Failed:', err);
    return null;
  }
}

async function handlePollJobProgress(payload, sendResponse) {
  const { jobId } = payload || {};
  if (!jobId) {
    sendResponse({
      success: false,
      errorCode: 'MISSING_JOB_ID',
      message: 'Job ID required'
    });
    return;
  }

  try {
    const response = await fetch(`${BACKEND_URL}/job/${jobId}/progress`);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const progress = await response.json();

    broadcastProgress({
      step: progress.current_step,
      status: progress.status,
      message: progress.message,
      progress_percent: progress.progress_percent
    });

    sendResponse({ success: true, progress });
  } catch (err) {
    console.error('Poll job progress error', err);
    sendResponse({
      success: false,
      errorCode: 'POLL_ERROR',
      message: `Failed to poll: ${err.message}`
    });
  }
}

async function handleGetJobResult(payload, sendResponse) {
  const { jobId } = payload || {};
  if (!jobId) {
    sendResponse({
      success: false,
      errorCode: 'MISSING_JOB_ID',
      message: 'Job ID required'
    });
    return;
  }

  try {
    const response = await fetch(`${BACKEND_URL}/job/${jobId}/result`);

    if (response.status === 202) {
      sendResponse({
        success: false,
        errorCode: 'JOB_PROCESSING',
        message: 'Job still processing'
      });
      return;
    }

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const result = await response.json();

    sendResponse({ success: true, result });
  } catch (err) {
    console.error('Get job result error', err);
    sendResponse({
      success: false,
      errorCode: 'RESULT_ERROR',
      message: `Failed to get result: ${err.message}`
    });
  }
}

function sanitizeText(text) {
  if (!text) return '';
  return text
    .replace(/<[^>]*>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

async function handleGetAvatars(sendResponse) {
  try {
    const response = await fetch(`${BACKEND_URL}/api/avatars`);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    sendResponse({ success: true, avatars: data.avatars || [] });
  } catch (err) {
    console.error('Get avatars error', err);
    sendResponse({
      success: false,
      errorCode: 'AVATARS_ERROR',
      message: `Failed to get avatars: ${err.message}`,
      avatars: []
    });
  }
}

async function handleGetVoices(sendResponse) {
  try {
    const response = await fetch(`${BACKEND_URL}/api/voices`);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    sendResponse({ success: true, voices: data.voices || [] });
  } catch (err) {
    console.error('Get voices error', err);
    sendResponse({
      success: false,
      errorCode: 'VOICES_ERROR',
      message: `Failed to get voices: ${err.message}`,
      voices: []
    });
  }
}

function broadcastProgress({ step, status, message, progress_percent }) {
  chrome.runtime.sendMessage({
    type: 'VIDEO_PROGRESS',
    payload: { step, status, message, progress_percent }
  }).catch(() => { });
}
