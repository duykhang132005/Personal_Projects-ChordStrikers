"""Report-only Content-Security-Policy header and the /csp-report sink."""
import json

from flask import Response, current_app, request


_REPORT_TYPES = frozenset({
    'application/csp-report',
    'application/reports+json',
})

# Fields taken from a report body, in preference order.
_DIRECTIVE_KEYS = ('effective-directive', 'effectiveDirective', 'violated-directive', 'violatedDirective')
_BLOCKED_KEYS = ('blocked-uri', 'blockedURI', 'blocked-url', 'blockedURL')
_DOCUMENT_KEYS = ('document-uri', 'documentURI', 'document-url', 'documentURL')


def build_csp_policy(report_path='/csp-report'):
    """Build the report-only policy string.

    script-src is 'self' only (no third-party scripts). font-src still allows
    jsdelivr because vendor.min.css loads Bootstrap Icons from that CDN.
    style-src is 'self' only: existing inline <style> blocks and style= attributes
    will show up as reports rather than being allowed. img-src allows
    https: so album covers from Apple and Spotify CDNs still load.
    """
    return (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "img-src 'self' data: https:; "
        "font-src 'self' https://cdn.jsdelivr.net; "
        "connect-src 'self'; "
        "manifest-src 'self'; "
        "worker-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "object-src 'none'; "
        f"report-uri {report_path}; "
        "report-to csp-endpoint"
    )


def _pick(mapping, keys):
    if not isinstance(mapping, dict):
        return ''
    for key in keys:
        value = mapping.get(key)
        if value:
            return value
    return ''


def _one_line(value, limit=120):
    text = '' if value is None else str(value)
    return text.replace('\n', ' ').replace('\r', ' ')[:limit]


def _iter_report_bodies(payload):
    """Yield CSP violation body dicts from either reporting format."""
    if isinstance(payload, dict):
        if isinstance(payload.get('csp-report'), dict):
            yield payload['csp-report']
            return
        if isinstance(payload.get('body'), dict):
            yield payload['body']
            return
        # A single flattened report object.
        yield payload
        return
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict) and isinstance(item.get('body'), dict):
                yield item['body']
            elif isinstance(item, dict):
                yield item


def _log_report(body):
    directive = _one_line(_pick(body, _DIRECTIVE_KEYS))
    blocked = _one_line(_pick(body, _BLOCKED_KEYS))
    document = _one_line(_pick(body, _DOCUMENT_KEYS))
    current_app.logger.info(
        'CSP report directive=%s blocked=%s document=%s',
        directive or '-',
        blocked or '-',
        document or '-',
    )


def csp_report():
    """Accept a browser CSP report. Always 204 on a well-sized body.

    CSRF-exempt so the browser can POST here without a token. The body is
    capped (default 8 KB) before it is parsed; oversized requests return 413
    without the HTML error page used for oversized form posts.
    """
    max_bytes = int(current_app.config.get('CSP_REPORT_MAX_BYTES', 8192))
    length = request.content_length
    if length is not None and length > max_bytes:
        return Response(status=413)

    buf = bytearray()
    stream = request.stream
    while True:
        chunk = stream.read(1024)
        if not chunk:
            break
        buf.extend(chunk)
        if len(buf) > max_bytes:
            return Response(status=413)

    content_type = (request.content_type or '').split(';', 1)[0].strip().lower()
    if content_type not in _REPORT_TYPES:
        current_app.logger.info('CSP report ignored: unsupported content type')
        return Response(status=204)

    if not buf:
        return Response(status=204)

    try:
        payload = json.loads(bytes(buf).decode('utf-8'))
    except (ValueError, UnicodeError):
        current_app.logger.info('CSP report ignored: invalid json')
        return Response(status=204)

    bodies = list(_iter_report_bodies(payload))
    if not bodies:
        current_app.logger.info('CSP report ignored: empty body')
        return Response(status=204)
    for body in bodies[:5]:
        _log_report(body)
    return Response(status=204)


def register_csp(app):
    """Attach the report-only header to every response and register the sink."""
    path = app.config.get('CSP_REPORT_PATH', '/csp-report')
    app.add_url_rule(path, endpoint='csp_report', view_func=csp_report, methods=['POST'])

    from . import csrf
    csrf.exempt(csp_report)

    @app.after_request
    def add_csp_report_only(response):
        if not app.config.get('CSP_REPORT_ONLY', True):
            return response
        report_path = app.config.get('CSP_REPORT_PATH', '/csp-report')
        response.headers['Content-Security-Policy-Report-Only'] = build_csp_policy(report_path)
        response.headers['Reporting-Endpoints'] = f'csp-endpoint="{report_path}"'
        return response
