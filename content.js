// content.js
// Tracks the user's current text selection on the page and
// responds to background requests for that selection.
// Stores selection in chrome.storage.local on mouseup for persistence.

let currentSelectionText = '';

function updateSelectionFromWindow() {
  const selection = window.getSelection();
  if (!selection || selection.rangeCount === 0) {
    currentSelectionText = '';
    return;
  }
  const text = selection.toString();
  currentSelectionText = sanitizeText(text);
}

// Update selection on selectionchange (debounce-like behavior)
document.addEventListener('selectionchange', () => {
  updateSelectionFromWindow();
});

// Store selection in chrome.storage on mouseup for popup access
document.addEventListener('mouseup', () => {
  const text = window.getSelection().toString().trim();
  if (text) {
    const sanitized = sanitizeText(text);
    if (sanitized) {
      try {
        chrome.storage.local.set({ 
          selectedText: sanitized,
          selectionTimestamp: Date.now(),
          selectionUrl: window.location.href
        });
      } catch (error) {
        // Extension context invalidated - this happens when extension is reloaded
        // Silently ignore as user just needs to refresh the page
        console.log('[Strang] Extension context invalidated. Please refresh the page.');
      }
    }
  }
});

// Handle messages from background script
try {
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'GET_SELECTION') {
      sendResponse({ text: currentSelectionText });
    }
  });
} catch (error) {
  // Extension context invalidated - user needs to refresh the page
  console.log('[Strang] Extension context invalidated. Please refresh the page.');
}

function sanitizeText(text) {
  if (!text) return '';
  const stripped = text
    .replace(/<[^>]*>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  return stripped;
}
