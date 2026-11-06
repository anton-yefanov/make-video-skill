#!/usr/bin/env node
// Renders a scene.html to MP4 frame-by-frame (deterministic, not real-time).
// Scene contract: window.SCENE = {width, height, fps, duration} and
// window.renderFrame(t /* seconds */) -> void | Promise. Optional window.ready Promise.
// Usage:
//   node render.mjs scene.html out.mp4 [--audio song.wav] [--crf 18]
//   node render.mjs scene.html --stills 0,5.2,12 --outdir previews   (PNG stills for review)
import puppeteer from 'puppeteer-core';
import { spawn } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import http from 'node:http';
import path from 'node:path';

const args = process.argv.slice(2);
const flag = (n, d) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : d; };
const scene = path.resolve(args[0] ?? '');
if (!args[0] || !existsSync(scene)) { console.error('usage: render.mjs scene.html out.mp4 [--audio f] | --stills t1,t2 --outdir d'); process.exit(1); }
const stills = flag('--stills');
const out = stills ? null : path.resolve(args[1]);
const audio = flag('--audio');
const crf = flag('--crf', '18');

const CHROME = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: true,
  args: ['--use-angle=metal', '--enable-gpu', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'],
});
const page = await browser.newPage();
page.on('console', m => console.log('[scene]', m.text()));
page.on('pageerror', e => { console.error('[scene error]', e.message); process.exitCode = 1; });
// serve the run folder over http: ES modules + fetch don't work from file://
const root = path.dirname(scene);
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.glb': 'model/gltf-binary', '.wav': 'audio/wav', '.mp3': 'audio/mpeg', '.mp4': 'video/mp4', '.webm': 'video/webm', '.woff2': 'font/woff2', '.ttf': 'font/ttf' };
const server = http.createServer((req, res) => {
  const f = path.join(root, decodeURIComponent(new URL(req.url, 'http://x').pathname));
  if (!f.startsWith(root) || !existsSync(f)) { res.writeHead(404).end(); return; }
  try { res.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream' }).end(readFileSync(f)); }
  catch { res.writeHead(404).end(); }
}).listen(0, '127.0.0.1');
await new Promise(r => server.once('listening', r));
await page.goto(`http://127.0.0.1:${server.address().port}/${path.basename(scene)}`, { waitUntil: 'networkidle0' });
await page.waitForFunction('window.SCENE && window.renderFrame', { timeout: 30000 });
await page.evaluate(() => window.ready);
const S = await page.evaluate(() => window.SCENE);
await page.setViewport({ width: S.width, height: S.height, deviceScaleFactor: 1 });

const shoot = async (t, type = 'jpeg') => {
  await page.evaluate(t => window.renderFrame(t), t);
  // two rAFs so WebGL/canvas content is composited before capture
  await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
  return page.screenshot({ type, quality: type === 'jpeg' ? 95 : undefined, clip: { x: 0, y: 0, width: S.width, height: S.height } });
};

if (stills) {
  const dir = path.resolve(flag('--outdir', 'previews'));
  mkdirSync(dir, { recursive: true });
  for (const t of stills.split(',').map(Number)) {
    const buf = await shoot(t, 'png');
    const f = path.join(dir, `t${t.toFixed(2)}.png`);
    writeFileSync(f, buf);
    console.log(f);
  }
} else {
  const total = Math.round(S.duration * S.fps);
  const ff = spawn('ffmpeg', [
    '-y', '-f', 'image2pipe', '-framerate', String(S.fps), '-i', '-',
    ...(audio ? ['-i', path.resolve(audio), '-c:a', 'aac', '-b:a', '192k', '-shortest'] : []),
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', crf, '-preset', 'medium', '-movflags', '+faststart', out,
  ], { stdio: ['pipe', 'inherit', 'inherit'] });
  const t0 = Date.now();
  for (let i = 0; i < total; i++) {
    const buf = await shoot(i / S.fps);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % S.fps === 0) process.stdout.write(`\rframe ${i}/${total}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  ff.stdin.end();
  const code = await new Promise(r => ff.on('close', r));
  console.log(`\n${code === 0 ? 'wrote ' + out : 'ffmpeg failed: ' + code}`);
  if (code !== 0) process.exitCode = 1;
}
await browser.close();
server.close();
