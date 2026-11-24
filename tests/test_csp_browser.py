"""Collect CSP report-only violations on the main pages.

Inline style= attributes and <style> blocks are expected today and do not
fail this test. script-src-attr (onclick-style handlers) and any script
blocked from an unexpected host, or eval, do fail. Inline <script> tags
that already live in index.html and explore.html are recorded so they can
be listed, but they do not fail the suite until those scripts are moved
out of the templates.
"""
import pytest

# Shared real-browser fixtures (a live server, Chromium, an admin login).
from browser_fixtures import (  # noqa: E402,F401
    _PW, admin_state, browser, live_server, register_in_browser,
)

pytestmark = pytest.mark.browser

# Chrome reports these blockedURI values for inline classic scripts and
# <script type="speculationrules"> already present in the templates.
_KNOWN_INLINE = frozenset({'inline', ''})

_COLLECT_SCRIPT = """
window.__cspViolations = [];
document.addEventListener('securitypolicyviolation', function (event) {
    window.__cspViolations.push({
        effectiveDirective: event.effectiveDirective || '',
        violatedDirective: event.violatedDirective || '',
        blockedURI: event.blockedURI || '',
        sourceFile: event.sourceFile || '',
        lineNumber: event.lineNumber || 0,
        columnNumber: event.columnNumber || 0,
        sample: event.sample || '',
        documentURI: event.documentURI || ''
    });
});
"""


def _collect(page):
    return page.evaluate('window.__cspViolations || []')


def _open(browser, live_server, admin_state, path):
    context = browser.new_context(
        storage_state=admin_state,
        service_workers='block',
    )
    context.add_init_script(_COLLECT_SCRIPT)
    page = context.new_page()
    console = []
    page.on('console', lambda msg: console.append(f'{msg.type}: {msg.text}'))
    page.goto(f"{live_server['base']}{path}", wait_until='load')
    # Deferred page scripts run after load.
    page.wait_for_timeout(500)
    violations = _collect(page)
    context.close()
    return violations, console


def _is_script(item):
    directive = (item.get('effectiveDirective') or item.get('violatedDirective') or '')
    return directive.startswith('script-src')


def _is_style(item):
    directive = (item.get('effectiveDirective') or item.get('violatedDirective') or '')
    return directive.startswith('style-src')


def _script_should_fail(item):
    directive = item.get('effectiveDirective') or item.get('violatedDirective') or ''
    blocked = item.get('blockedURI') or ''
    if directive == 'script-src-attr':
        return True
    if 'eval' in blocked or blocked == 'wasm-eval' or blocked == 'wasm-unsafe-eval':
        return True
    if directive.startswith('script-src') and blocked not in _KNOWN_INLINE:
        return True
    return False


def test_csp_violations_on_home_explore_sheet_and_create(browser, live_server, admin_state):
    song_id = live_server['song_id']
    paths = [
        ('/', 'home'),
        ('/explore', 'explore'),
        (f'/view_sheet/{song_id}', 'view_sheet'),
        ('/create', 'create'),
    ]
    by_page = {}
    unexpected_scripts = []
    all_items = []
    for path, label in paths:
        violations, console = _open(browser, live_server, admin_state, path)
        by_page[label] = {'path': path, 'violations': violations, 'console': console}
        for item in violations:
            tagged = dict(item)
            tagged['page'] = label
            tagged['path'] = path
            all_items.append(tagged)
            if _script_should_fail(tagged):
                unexpected_scripts.append(tagged)

    def fmt(item):
        return (
            f"{item.get('page')}: {item.get('effectiveDirective')} "
            f"blocked={item.get('blockedURI')!r} "
            f"line={item.get('lineNumber')} "
            f"sample={item.get('sample')!r} "
            f"source={item.get('sourceFile')}"
        )

    style_items = [item for item in all_items if _is_style(item)]
    script_items = [item for item in all_items if _is_script(item)]
    print('CSP style violations (informational):')
    for item in style_items:
        print('  ', fmt(item))
    print('CSP script violations (inline <script> tags are known):')
    for item in script_items:
        print('  ', fmt(item))

    assert not unexpected_scripts, (
        'Unexpected script-src CSP violations:\n' +
        '\n'.join(fmt(item) for item in unexpected_scripts)
    )
    # The report-only header must be present so the listener can fire at all
    # (style violations on home/explore are expected today).
    assert home_or_any(style_items, script_items, by_page)


def home_or_any(style_items, script_items, by_page):
    if style_items or script_items:
        return True
    raise AssertionError(
        'Expected at least one report-only CSP event on these pages '
        '(index.html has an inline <style> block). Got none; the header '
        'may be missing or the listener ran too late. Console: '
        + repr({label: info['console'] for label, info in by_page.items()})
    )
