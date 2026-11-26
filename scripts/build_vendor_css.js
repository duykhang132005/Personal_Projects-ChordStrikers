/* Rebuild static/vendor/vendor.min.css: Bootstrap 5.3.3 and Bootstrap Icons
 * 1.11.3, trimmed to the classes that appear in
 * templates/, static/js/ and app/. Run after adding a new Bootstrap class or
 * icon, from the project root:
 *
 *   npm install --no-save purgecss@6 clean-css@5
 *   node scripts/build_vendor_css.js
 *
 * Node is only needed for this build; the site itself does not use it.
 * It also saves the Bootstrap Icons woff2 to static/fonts/ so the icon font is
 * self-hosted (no CDN at runtime). The older woff fallback is dropped.
 */
const fs = require('fs');
const path = require('path');
const https = require('https');
const { PurgeCSS } = require('purgecss');
const CleanCSS = require('clean-css');

const ROOT = path.resolve(__dirname, '..');
const SOURCES = {
  bootstrap: 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css',
  icons: 'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css',
  iconsFont: 'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/fonts/bootstrap-icons.woff2',
};
const CONTENT = ['templates/**/*.html', 'static/js/**/*.js', 'app/**/*.py'].map((p) => path.join(ROOT, p).replace(/\\/g, '/'));
// Classes Bootstrap JS adds at runtime, or that are built from template variables.
const SAFELIST = {
  standard: [/^alert/, 'fade', 'show', 'btn-close', 'visually-hidden', 'visually-hidden-focusable',
    'd-none', 'active', 'disabled', 'collapse', 'collapsing', 'showing', 'hiding'],
  greedy: [/^alert-/],
};

function download(url) {
  return new Promise((resolve, reject) => {
    https.get(url, (res) => {
      if (res.statusCode !== 200) { reject(new Error(url + ' ' + res.statusCode)); return; }
      let body = '';
      res.setEncoding('utf8');
      res.on('data', (chunk) => { body += chunk; });
      res.on('end', () => resolve(body));
    }).on('error', reject);
  });
}

function downloadBinary(url) {
  return new Promise((resolve, reject) => {
    https.get(url, (res) => {
      if (res.statusCode !== 200) { reject(new Error(url + ' ' + res.statusCode)); return; }
      const chunks = [];
      res.on('data', (chunk) => { chunks.push(chunk); });
      res.on('end', () => resolve(Buffer.concat(chunks)));
    }).on('error', reject);
  });
}

async function purge(css) {
  const [result] = await new PurgeCSS().purge({
    content: CONTENT, css: [{ raw: css }], safelist: SAFELIST,
    fontFace: false, keyframes: true, variables: false,
  });
  return result.css;
}

(async () => {
  const bootstrap = await purge(await download(SOURCES.bootstrap));
  const icons = (await purge(await download(SOURCES.icons)))
    .replace(/,\s*url\("\.\/fonts\/bootstrap-icons\.woff\?[^"]*"\)\s*format\("woff"\)/g, '')
    .replace(/url\("\.\/fonts\//g, 'url("../fonts/');
  const font = await downloadBinary(SOURCES.iconsFont);
  const fontOut = path.join(ROOT, 'static', 'fonts', 'bootstrap-icons.woff2');
  fs.mkdirSync(path.dirname(fontOut), { recursive: true });
  fs.writeFileSync(fontOut, font);
  console.log('Wrote', fontOut, font.length, 'bytes');
  const header = '/* Bootstrap 5.3.3 (MIT), Bootstrap Icons 1.11.3 (MIT).\n'
    + '   Trimmed to the classes ChordStrikers uses. Rebuild with scripts/build_vendor_css.js. */\n';
  const css = new CleanCSS({ level: 1 }).minify(bootstrap + '\n' + icons).styles
    .replace(/@charset "UTF-8";/g, '');
  const out = path.join(ROOT, 'static', 'vendor', 'vendor.min.css');
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, (header + css + '\n').replace(/\r?\n/g, '\r\n'));
  console.log('Wrote', out, css.length, 'bytes');
})().catch((err) => { console.error(err); process.exit(1); });
