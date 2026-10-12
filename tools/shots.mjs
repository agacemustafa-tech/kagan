// Makes Google Play store screenshots (1080x1920) and the feature graphic (1024x500)
// from the real game. Run from the repo root: node tools/shots.mjs <outDir>
import { chromium } from 'playwright';
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';

const OUT = process.argv[2] || 'store-out';
fs.mkdirSync(OUT, { recursive: true });

// test copy of the game with a few hooks for staging scenes
let src = fs.readFileSync('index.html', 'utf8');
const HOOK = "let DL=1;window.__t={setLv:v=>{level=v;startLevel();updateHud();},boss:()=>spawnBoss(),power:n=>{player.power=n;updateHud();},heal:()=>{player.hp=player.max;updateHud();},waves:n=>{for(let i=0;i<n;i++)spawnWave();},noBanner:()=>{banner=null;}};";
if (!src.includes('let DL=1;')) throw new Error('hook point missing');
fs.writeFileSync('_shot.html', src.replace('let DL=1;', HOOK));

const types = { '.html': 'text/html; charset=utf-8', '.png': 'image/png', '.webmanifest': 'application/manifest+json', '.js': 'text/javascript' };
const server = http.createServer((req, res) => {
  const f = path.join(process.cwd(), decodeURIComponent(req.url.split('?')[0]).replace(/^\/+/, '') || '_shot.html');
  if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { 'content-type': types[path.extname(f)] || 'application/octet-stream' });
  fs.createReadStream(f).pipe(res);
}).listen(8765);
const URL = 'http://localhost:8765/_shot.html';

const today = new Date(), y = new Date(); y.setDate(y.getDate() - 1);
const dk = d => d.getFullYear() + '-' + (d.getMonth() + 1) + '-' + d.getDate();
const wait = ms => new Promise(r => setTimeout(r, ms));

const browser = await chromium.launch();
let heroPng = null;

for (const lang of ['tr', 'en', 'ru']) {
  const dir = path.join(OUT, 'screenshots-' + lang); fs.mkdirSync(dir, { recursive: true });
  const ctx = await browser.newContext({ viewport: { width: 360, height: 640 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true });
  const pg = await ctx.newPage();
  const prep = async (login) => {
    await pg.goto(URL);
    await pg.evaluate(([lang, login]) => {
      localStorage.clear();
      localStorage.setItem('kaanLang', JSON.stringify(lang));
      localStorage.setItem('kaanHelped', '1');
      localStorage.setItem('kaanCoins', '12450');
      localStorage.setItem('kaanGems', '85');
      localStorage.setItem('kaanSet', JSON.stringify({ sfx: false, mus: false, vib: false, shake: false }));
      localStorage.setItem('kaanLogin', JSON.stringify(login));
    }, [lang, login]);
    await pg.reload(); await pg.evaluate(() => document.fonts && document.fonts.ready); await wait(1500);
  };
  const shot = async (n) => pg.screenshot({ path: path.join(dir, n + '.png') });

  // 1 menu
  await prep({ last: dk(today), streak: 1 });
  await shot('1-menu');
  if (!heroPng) heroPng = await pg.evaluate(() => document.getElementById('hero').toDataURL('image/png'));

  // 2 gameplay
  await pg.click('#play'); await wait(800);
  await pg.evaluate(() => { __t.setLv(3); __t.power(4); __t.noBanner(); });
  await pg.mouse.move(180, 520);
  for (let i = 0; i < 6; i++) { await pg.evaluate(() => { __t.heal(); __t.waves(1); }); await wait(900); }
  await pg.evaluate(() => __t.noBanner());
  await shot('2-oyun');

  // 3 hard level boss
  await pg.evaluate(() => { __t.setLv(5); __t.heal(); __t.noBanner(); __t.boss(); });
  for (let i = 0; i < 5; i++) { await pg.evaluate(() => __t.heal()); await wait(900); }
  await shot('3-anagemi');

  // 4 hangar
  await prep({ last: dk(today), streak: 1 });
  await pg.click('#toHangar1'); await wait(2500);
  await shot('4-hangar');

  // 5 daily reward
  await prep({ last: dk(y), streak: 3 }); await wait(500);
  await shot('5-gunluk-odul');

  // 6 workshop upgrades
  await prep({ last: dk(today), streak: 1 });
  await pg.click('#toShop'); await wait(800);
  await shot('6-atolye');
  await ctx.close();
}

// feature graphic 1024x500
const fctx = await browser.newContext({ viewport: { width: 1024, height: 500 }, deviceScaleFactor: 1 });
const fp = await fctx.newPage();
await fp.setContent(`<!doctype html><html><head><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Russo+One&display=swap">
<style>html,body{margin:0;width:1024px;height:500px;overflow:hidden}
body{background:radial-gradient(ellipse at 72% 50%,#1f5d8f 0%,#123a5c 38%,#0c1f33 75%);font-family:"Russo One",sans-serif;position:relative}
.cl{position:absolute;border-radius:50%;background:rgba(255,255,255,.08);filter:blur(6px)}
h1{position:absolute;left:64px;top:118px;margin:0;font-size:150px;line-height:1;color:#eef6ff;letter-spacing:4px;font-weight:400;text-shadow:0 8px 0 #e30a17,0 24px 40px rgba(0,0,0,.6)}
p{position:absolute;left:70px;top:312px;margin:0;font-size:34px;letter-spacing:10px;color:#ffc940}
img{position:absolute;right:40px;top:-10px;width:520px;height:520px;transform:rotate(-12deg);filter:drop-shadow(0 30px 30px rgba(0,0,0,.55))}
</style></head><body>
<div class="cl" style="left:520px;top:40px;width:260px;height:90px"></div><div class="cl" style="left:760px;top:380px;width:300px;height:110px"></div><div class="cl" style="left:-60px;top:420px;width:340px;height:120px"></div>
<h1>KAĞAN</h1><p>SKY GUARDIAN</p><img src="${heroPng}"></body></html>`);
await fp.evaluate(() => document.fonts.ready); await wait(800);
await fp.screenshot({ path: path.join(OUT, 'feature-graphic-1024x500.png') });

await browser.close();
server.close();
fs.unlinkSync('_shot.html');
console.log('shots done');
