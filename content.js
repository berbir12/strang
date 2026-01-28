// content.js
// Tracks the user's current text selection on the page and
// responds to background requests for that selection.

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

document.addEventListener('selectionchange', () => {
  // Debounce-like behavior: this event can fire a lot but the logic is cheap.
  updateSelectionFromWindow();
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'GET_SELECTION') {
    sendResponse({ text: currentSelectionText });
  }
});

function sanitizeText(text) {
  if (!text) return '';
  const stripped = text
    .replace(/<[^>]*>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  return stripped;
}

