// aiMock.js
// Mock AI backend for generating an explainer video plan.
// This simulates the /generate-video API pipeline:
// 1) Text simplification
// 2) Scene/storyboard generation
// 3) Voiceover script generation

/**
 * @typedef {Object} GenerateVideoInput
 * @property {string} text
 * @property {string} style
 * @property {number} duration
 * @property {string} voiceAccent
 */

/**
 * @typedef {Object} Scene
 * @property {number} id
 * @property {string} title
 * @property {string} slideText
 * @property {string} visualDescription
 * @property {string} animationDirective
 * @property {number} startTime
 * @property {number} endTime
 */

/**
 * @typedef {Object} VideoPlan
 * @property {string} teachingScript
 * @property {string[]} bulletBreakdown
 * @property {string[]} keyConcepts
 * @property {Scene[]} scenes
 * @property {string} voiceoverScript
 * @property {{ duration: number, style: string, voiceAccent: string }} meta
 */

/**
 * Main mock entrypoint that simulates an AI video generation pipeline.
 * @param {GenerateVideoInput} input
 * @returns {Promise<VideoPlan>}
 */
export async function generateVideoPlan(input) {
  const { text, style, duration, voiceAccent } = input;

  // Simulate small latency for more realistic progress UX
  await delay(150);

  const normalizedText = (text || '').trim();

  const teachingScript = buildTeachingScript(normalizedText, style);
  const bulletBreakdown = buildBulletBreakdown(normalizedText);
  const keyConcepts = extractKeyConcepts(normalizedText);

  // Step 2: scenes
  const scenes = buildScenes({
    teachingScript,
    bulletBreakdown,
    duration
  });

  // Step 3: voiceover
  const voiceoverScript = buildVoiceoverScript({
    teachingScript,
    bulletBreakdown,
    style
  });

  return {
    teachingScript,
    bulletBreakdown,
    keyConcepts,
    scenes,
    voiceoverScript,
    meta: {
      duration,
      style,
      voiceAccent
    }
  };
}

function buildTeachingScript(text, style) {
  const base = text.length > 600 ? text.slice(0, 600) + '…' : text;
  switch (style) {
    case 'academic':
      return `In summary, ${base} This explanation maintains a more formal and analytical tone, emphasizing definitions, structure, and underlying principles.`;
    case 'child-friendly':
      return `Imagine we are explaining this to a curious kid. In simple words: ${base} We keep sentences short, friendly, and full of examples so it is easy to follow.`;
    case 'technical':
      return `From a technical perspective, ${base} The explanation focuses on mechanisms, constraints, and edge cases, using precise terminology.`;
    case 'simple':
    default:
      return `Here is a clear, concise explanation: ${base} The goal is to keep it straightforward and easy to understand without unnecessary jargon.`;
  }
}

function buildBulletBreakdown(text) {
  const sentences = splitIntoSentences(text).slice(0, 6);
  if (!sentences.length) {
    return ['Core idea not detected from the input text.'];
  }
  return sentences.map((s) => `• ${s.trim()}`);
}

function extractKeyConcepts(text) {
  const lowered = text.toLowerCase();
  const words = lowered
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter(Boolean);

  const freq = new Map();
  for (const w of words) {
    if (w.length < 4) continue;
    freq.set(w, (freq.get(w) || 0) + 1);
  }
  const sorted = Array.from(freq.entries()).sort((a, b) => b[1] - a[1]);
  return sorted
    .slice(0, 6)
    .map(([w]) => w)
    .filter(Boolean);
}

function buildScenes({ teachingScript, bulletBreakdown, duration }) {
  const desiredScenes = Math.min(Math.max(bulletBreakdown.length, 3), 8);
  const perScene = duration / desiredScenes;

  const scenes = [];
  for (let i = 0; i < desiredScenes; i += 1) {
    const startTime = Math.round(i * perScene * 10) / 10;
    const endTime = Math.round((i + 1) * perScene * 10) / 10;

    const bullet = bulletBreakdown[i] || bulletBreakdown[bulletBreakdown.length - 1] || teachingScript;
    const shortTitle = `Scene ${i + 1}`;
    const animationDirective = i === 0 ? 'fade-in' : i % 2 === 0 ? 'slide-left' : 'slide-right';

    scenes.push({
      id: i + 1,
      title: shortTitle,
      slideText: bullet.replace(/^•\s*/, ''),
      visualDescription:
        'Minimal, clean slide with large heading, supporting text, and subtle shapes to guide the viewer focus.',
      animationDirective,
      startTime,
      endTime
    });
  }

  return scenes;
}

function buildVoiceoverScript({ teachingScript, bulletBreakdown, style }) {
  const bulletsJoined = bulletBreakdown
    .map((b) => b.replace(/^•\s*/, ''))
    .join(' ');
  const styleNote =
    style === 'child-friendly'
      ? 'The narrator speaks warmly and clearly, using everyday language and analogies.'
      : style === 'academic'
      ? 'The narrator uses a measured, formal tone while remaining understandable.'
      : style === 'technical'
      ? 'The narrator focuses on precision, briefly calling out important definitions and edge cases.'
      : 'The narrator keeps a friendly, approachable tone, focusing on clarity.';

  return `${teachingScript}\n\nNow, here is the key progression: ${bulletsJoined}\n\n${styleNote}`;
}

function splitIntoSentences(text) {
  if (!text) return [];
  return text
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

