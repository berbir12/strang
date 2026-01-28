// videoRenderer.js
// Responsible for composing a simple animated explainer video
// using an HTMLCanvasElement and MediaRecorder.
//
// The popup passes the AI plan (scenes, voiceover, meta) and
// this module returns a Blob, object URL, and basic subtitle data.

/**
 * Render an explainer video for the given plan into a canvas.
 * @param {HTMLCanvasElement} canvas
 * @param {import('./aiMock.js').VideoPlan} plan
 * @param {{ theme: 'light' | 'dark' }} options
 * @returns {Promise<{ blob: Blob, url: string, srt: string, timings: any }>}
 */
export async function renderExplainerVideo(canvas, plan, options = { theme: 'light' }) {
  const { scenes, meta } = plan;
  const duration = meta?.duration || 60;
  const fps = 24;

  // Setup canvas size (16:9)
  canvas.width = 1280;
  canvas.height = 720;

  const ctx = canvas.getContext('2d');
  if (!ctx) {
    throw new Error('Canvas 2D context is not available.');
  }

  const theme = options.theme === 'dark' ? 'dark' : 'light';

  const stream = canvas.captureStream(fps);
  const mimeTypeOptions = [
    'video/webm;codecs=vp9',
    'video/webm;codecs=vp8',
    'video/webm'
  ];
  const mimeType = mimeTypeOptions.find((mt) => MediaRecorder.isTypeSupported(mt)) || 'video/webm';

  const recorder = new MediaRecorder(stream, { mimeType });
  const chunks = [];

  recorder.ondataavailable = (e) => {
    if (e.data && e.data.size > 0) {
      chunks.push(e.data);
    }
  };

  const totalFrames = Math.ceil(duration * fps);
  const sceneTimings = scenes.map((scene) => ({
    id: scene.id,
    title: scene.title,
    slideText: scene.slideText,
    startTime: scene.startTime,
    endTime: scene.endTime
  }));

  const subtitles = scenes.map((scene, index) => ({
    index: index + 1,
    start: scene.startTime,
    end: scene.endTime,
    text: scene.slideText
  }));

  const renderLoop = () =>
    new Promise((resolve) => {
      let frame = 0;
      const start = performance.now();

      const drawFrame = () => {
        const now = performance.now();
        const elapsedSec = (now - start) / 1000;
        if (elapsedSec >= duration || frame >= totalFrames) {
          resolve();
          return;
        }

        const currentScene = scenes.find(
          (s) => elapsedSec >= s.startTime && elapsedSec < s.endTime
        ) || scenes[scenes.length - 1];

        drawSceneFrame(ctx, canvas, currentScene, elapsedSec, theme);

        frame += 1;
        requestAnimationFrame(drawFrame);
      };

      requestAnimationFrame(drawFrame);
    });

  const promise = new Promise((resolve, reject) => {
    recorder.onstop = () => {
      try {
        const blob = new Blob(chunks, { type: mimeType });
        const url = URL.createObjectURL(blob);
        const srt = buildSrt(subtitles);
        resolve({
          blob,
          url,
          srt,
          timings: { subtitles, sceneTimings, duration, fps }
        });
      } catch (err) {
        reject(err);
      }
    };
    recorder.onerror = (e) => {
      reject(e.error || e);
    };
  });

  recorder.start();
  await renderLoop();
  recorder.stop();

  return promise;
}

function drawSceneFrame(ctx, canvas, scene, elapsedSec, theme) {
  const { width, height } = canvas;
  const sceneStart = scene.startTime;
  const sceneEnd = scene.endTime;
  const sceneDuration = Math.max(sceneEnd - sceneStart, 0.1);
  const tInScene = elapsedSec - sceneStart;
  const progress = Math.min(Math.max(tInScene / sceneDuration, 0), 1);

  const isDark = theme === 'dark';

  // Background
  ctx.fillStyle = isDark ? '#020617' : '#f9fafb';
  ctx.fillRect(0, 0, width, height);

  // Decorative shapes
  ctx.save();
  ctx.globalAlpha = 0.12;
  ctx.fillStyle = isDark ? '#4f46e5' : '#2563eb';
  ctx.beginPath();
  ctx.arc(width * 0.15, height * 0.2, 120, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = isDark ? '#0ea5e9' : '#22c55e';
  ctx.beginPath();
  ctx.arc(width * 0.85, height * 0.85, 140, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();

  // Card container
  ctx.fillStyle = isDark ? '#020617' : '#ffffff';
  ctx.strokeStyle = isDark ? 'rgba(148, 163, 184, 0.4)' : 'rgba(148, 163, 184, 0.7)';
  ctx.lineWidth = 2;
  const cardPadding = 40;
  const cardX = cardPadding;
  const cardY = cardPadding * 1.4;
  const cardW = width - cardPadding * 2;
  const cardH = height - cardPadding * 2.3;
  roundRect(ctx, cardX, cardY, cardW, cardH, 18);

  // Title
  ctx.font = 'bold 40px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI"';
  ctx.textAlign = 'left';
  ctx.textBaseline = 'top';
  ctx.fillStyle = isDark ? '#e5e7eb' : '#111827';
  const title = scene.title || 'Scene';
  ctx.fillText(title, cardX + 32, cardY + 24);

  // Main text (slideText)
  const maxTextWidth = cardW - 64;
  const textLines = wrapText(ctx, scene.slideText || '', maxTextWidth, 28);

  const baseTextX =
    scene.animationDirective === 'slide-left'
      ? cardX + 32 + (1 - progress) * 80
      : scene.animationDirective === 'slide-right'
      ? cardX + 32 - (1 - progress) * 80
      : cardX + 32;

  const baseTextY = cardY + 90;

  const alpha =
    scene.animationDirective === 'fade-in'
      ? Math.min(progress * 1.2, 1)
      : 1;

  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.font = 'normal 26px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI"';
  ctx.fillStyle = isDark ? '#d1d5db' : '#4b5563';

  textLines.forEach((line, idx) => {
    ctx.fillText(line, baseTextX, baseTextY + idx * 32);
  });
  ctx.restore();

  // Subtitle bar (simple, reusing slideText)
  const subtitleText = scene.slideText || '';
  if (subtitleText) {
    const barH = 70;
    ctx.fillStyle = isDark ? 'rgba(15, 23, 42, 0.92)' : 'rgba(15, 23, 42, 0.9)';
    ctx.fillRect(0, height - barH, width, barH);

    ctx.font = 'normal 22px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI"';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = '#f9fafb';

    const subtitleLines = wrapText(ctx, subtitleText, width - 60, 26);
    const subtitleBaseY = height - barH / 2 - (subtitleLines.length - 1) * 13;
    subtitleLines.forEach((line, idx) => {
      ctx.fillText(line, width / 2, subtitleBaseY + idx * 26);
    });
  }
}

function roundRect(ctx, x, y, w, h, r) {
  const radius = typeof r === 'number' ? { tl: r, tr: r, br: r, bl: r } : r;
  ctx.beginPath();
  ctx.moveTo(x + radius.tl, y);
  ctx.lineTo(x + w - radius.tr, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + radius.tr);
  ctx.lineTo(x + w, y + h - radius.br);
  ctx.quadraticCurveTo(x + w, y + h, x + w - radius.br, y + h);
  ctx.lineTo(x + radius.bl, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - radius.bl);
  ctx.lineTo(x, y + radius.tl);
  ctx.quadraticCurveTo(x, y, x + radius.tl, y);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
}

function wrapText(ctx, text, maxWidth, lineHeight) {
  const words = (text || '').split(/\s+/);
  const lines = [];
  let current = '';

  for (const word of words) {
    const testLine = current ? `${current} ${word}` : word;
    const { width } = ctx.measureText(testLine);
    if (width > maxWidth && current) {
      lines.push(current);
      current = word;
    } else {
      current = testLine;
    }
  }
  if (current) lines.push(current);
  return lines.slice(0, Math.max(3, lines.length));
}

function buildSrt(subtitles) {
  return subtitles
    .map((entry) => {
      const start = formatSrtTime(entry.start);
      const end = formatSrtTime(entry.end);
      return `${entry.index}\n${start} --> ${end}\n${entry.text}\n`;
    })
    .join('\n');
}

function formatSrtTime(sec) {
  const totalMs = Math.floor(sec * 1000);
  const hours = Math.floor(totalMs / 3_600_000);
  const minutes = Math.floor((totalMs % 3_600_000) / 60_000);
  const seconds = Math.floor((totalMs % 60_000) / 1000);
  const ms = totalMs % 1000;

  const pad = (n, size) => String(n).padStart(size, '0');
  return `${pad(hours, 2)}:${pad(minutes, 2)}:${pad(seconds, 2)},${pad(ms, 3)}`;
}

