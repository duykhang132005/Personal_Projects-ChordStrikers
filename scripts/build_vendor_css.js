/* Rebuild static/vendor/vendor.min.css: Bootstrap 5.3.3, Bootstrap Icons
 * 1.11.3 and Font Awesome Free 6.5.0, trimmed to the classes that appear in
 * templates/, static/js/ and app/. Run after adding a new Bootstrap class or
 * icon, from the project root:
 *
 *   npm install --no-save purgecss@6 clean-css@5
 *   node scripts/build_vendor_css.js
 *
 * Node is only needed for this build; the site itself does not use it.
 * Icon fonts still load from the same CDNs, so their URLs are absolute.
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
  fontawesome: 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css',
};
const CONTENT = ['templates/**/*.html', 'static/js/**/*.js', 'app/**/*.py'].map((p) => path.join(ROOT, p));
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
    .replace(/url\("\.\/fonts\//g, 'url("https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/fonts/');
  const fontawesome = (await purge(await download(SOURCES.fontawesome)))
    .replace(/url\(\.\.\/webfonts\//g, 'url(https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/webfonts/')
    // Only the solid style (fas) is used.
    .replace(/@font-face\{[^}]*(fa-brands-400|fa-regular-400|fa-v4compatibility)[^}]*\}/g, '');
  const header = '/* Bootstrap 5.3.3 (MIT), Bootstrap Icons 1.11.3 (MIT), Font Awesome Free 6.5.0 '
    + '(icons CC BY 4.0, fonts OFL 1.1, code MIT).\n'
    + '   Trimmed to the classes ChordStrikers uses. Rebuild with scripts/build_vendor_css.js. */\n';
  const css = new CleanCSS({ level: 1 }).minify(bootstrap + '\n' + icons + '\n' + fontawesome).styles
    .replace(/@charset "UTF-8";/g, '');
  const out = path.join(ROOT, 'static', 'vendor', 'vendor.min.css');
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, (header + css + '\n').replace(/\r?\n/g, '\r\n'));
  console.log('Wrote', out, css.length, 'bytes');
})().catch((err) => { console.error(err); process.exit(1); });
