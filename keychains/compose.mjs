// Builds the Instagram posts (1080x1350, 4:5) from the renders.
//   node compose.mjs            -> instagram/post_*.png
// Edit BRAND / PRICES / POSTS below, then re-run. Needs Playwright (Chromium);
// a global install works with NODE_PATH=$(npm root -g).
import { createRequire } from 'module';
import { fileURLToPath } from 'url';
import path from 'path';
import fs from 'fs';

const { chromium } = createRequire(import.meta.url)('playwright');
const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, 'instagram');
const url = p => 'file://' + path.join(HERE, p);

const BRAND = '@ton.compte';          // <- your Instagram handle
const DELIVERY = 'Livraison partout en Tunisie';
const PRICES = [                      // <- your prices (TND)
  ['Porte-clés Drapeau / Khomsa', '7 DT'],
  ['Maillot · ton numéro', '8 DT'],
  ['Prénom personnalisé (arabe ou français)', '10 DT'],
  ['Pack de 3 au choix', '20 DT'],
  ['Pack de 5 au choix', '30 DT'],
  ['Mariage / événements (min. 30 pièces)', 'dès 3 DT/pièce'],
];

const POSTS = [
  { id: 'hero', render: 'hero', kicker: 'Fait en Tunisie 🇹🇳', title: 'Porte-clés<br>imprimés en 3D',
    sub: 'Personnalisés · solides · multicolores', badge: 'dès 7 DT' },
  { id: 'names', render: 'names', kicker: 'Personnalisé', title: 'Ton prénom, en arabe<br>ou en français',
    ar: 'اسمك بالعربي ولا بالفرنسي', badge: '10 DT' },
  { id: 'souvenir', render: 'souvenir', kicker: 'Souvenirs de Tunisie', title: 'Khomsa & drapeau',
    sub: 'Le cadeau parfait pour la famille à l’étranger', badge: '7 DT' },
  { id: 'jerseys', render: 'jerseys', kicker: 'Pour les supporters', title: 'Les couleurs<br>de ton club',
    sub: 'Choisis tes couleurs + ton numéro', badge: '8 DT' },
  { id: 'wedding', render: 'wedding', kicker: 'Mariage · Khotba · Sbou3', title: 'Cadeaux d’invités<br>personnalisés',
    sub: 'Vos initiales, vos couleurs', badge: 'dès 3 DT / pièce' },
  { id: 'prices', render: 'hero', prices: true },
];

const css = `
@font-face { font-family: Cairo; src: url('${url('fonts/Cairo.ttf')}'); font-weight: 200 1000; }
* { margin: 0; box-sizing: border-box; }
body { width: 1080px; height: 1350px; overflow: hidden; font-family: Cairo, sans-serif; color: #1d1d1f; }
.bg { position: absolute; inset: 0; background-size: cover; background-position: center; }
.fade { position: absolute; inset: 0 0 auto 0; height: 560px;
  background: linear-gradient(to bottom, rgba(255,255,255,.55), rgba(255,255,255,0)); }
.head { position: absolute; top: 70px; left: 80px; right: 80px; }
.kicker { display: inline-block; font-weight: 800; font-size: 30px; letter-spacing: .5px; color: #fff;
  background: #C8102E; padding: 4px 22px 6px; border-radius: 40px; }
h1 { font-weight: 900; font-size: 92px; line-height: 1.02; margin-top: 22px; letter-spacing: -1px; }
.sub { font-weight: 600; font-size: 36px; margin-top: 14px; color: #3a3a3c; }
.ar { font-weight: 800; font-size: 46px; margin-top: 10px; color: #C8102E; direction: rtl; text-align: left; }
.badge { position: absolute; right: 70px; bottom: 150px; background: #1d1d1f; color: #fff; font-weight: 900;
  font-size: 50px; padding: 14px 36px 18px; border-radius: 22px; transform: rotate(-4deg);
  box-shadow: 0 12px 30px rgba(0,0,0,.25); }
.foot { position: absolute; left: 0; right: 0; bottom: 0; height: 104px; background: #1d1d1f; color: #fff;
  display: flex; align-items: center; justify-content: space-between; padding: 0 70px;
  font-weight: 700; font-size: 31px; }
.foot b { color: #F6C312; font-weight: 900; }
.handle { position: absolute; top: 76px; right: 80px; font-weight: 800; font-size: 28px; opacity: .75; }
.card { position: absolute; left: 70px; right: 70px; top: 90px; bottom: 170px; background: rgba(255,255,255,.93);
  border-radius: 40px; padding: 60px 64px; box-shadow: 0 20px 60px rgba(0,0,0,.18); }
.card h1 { font-size: 84px; margin: 18px 0 30px; }
.row { display: flex; justify-content: space-between; align-items: baseline; gap: 30px; font-size: 38px;
  font-weight: 700; padding: 20px 0; border-bottom: 3px dashed #d8d2c8; }
.row:last-child { border: 0; }
.row span:last-child { font-weight: 900; color: #C8102E; white-space: nowrap; }
.blur { filter: blur(14px) saturate(1.1); transform: scale(1.1); }
`;

function html(p) {
  const bg = url(`renders/render_${p.render}.png`);
  const foot = `<div class="foot"><span>📩 Commande en <b>DM</b></span><span>🚚 ${DELIVERY}</span></div>`;
  if (p.prices) {
    const rows = PRICES.map(([a, b]) => `<div class="row"><span>${a}</span><span>${b}</span></div>`).join('');
    return `<html><head><meta charset="utf-8"><style>${css}</style></head><body>
      <div class="bg blur" style="background-image:url('${bg}')"></div>
      <div class="card"><span class="kicker">${BRAND}</span><h1>Nos prix</h1>${rows}</div>${foot}</body></html>`;
  }
  return `<html><head><meta charset="utf-8"><style>${css}</style></head><body>
    <div class="bg" style="background-image:url('${bg}')"></div><div class="fade"></div>
    <div class="handle">${BRAND}</div>
    <div class="head"><span class="kicker">${p.kicker}</span><h1>${p.title}</h1>
      ${p.sub ? `<div class="sub">${p.sub}</div>` : ''}${p.ar ? `<div class="ar">${p.ar}</div>` : ''}</div>
    <div class="badge">${p.badge}</div>${foot}</body></html>`;
}

fs.mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1080, height: 1350 } });
for (const p of POSTS) {
  const tmp = path.join(OUT, `.tmp_${p.id}.html`);
  fs.writeFileSync(tmp, html(p));
  await page.goto('file://' + tmp);
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: path.join(OUT, `post_${POSTS.indexOf(p) + 1}_${p.id}.png`) });
  fs.unlinkSync(tmp);
  console.log('wrote', `post_${POSTS.indexOf(p) + 1}_${p.id}.png`);
}
await browser.close();
