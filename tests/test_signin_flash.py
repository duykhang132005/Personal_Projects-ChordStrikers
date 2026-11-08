from html.parser import HTMLParser


def test_create_redirect_shows_one_signin_message(client):
    response = client.get('/create', follow_redirects=True)
    assert response.status_code == 200
    assert response.request.args.get('signin') == '1'
    html = response.get_data(as_text=True)
    assert html.count('Please log in to continue.') == 1
    assert html.count('id="signin-alert"') == 1
    assert 'class="container flash-stack"' not in html
    assert b'Please log in to continue.' not in client.get('/').data


def test_repeated_create_redirects_keep_one_prompt_and_other_flashes(client):
    # An abandoned redirect (including speculative navigation) can leave a
    # prompt queued before the user actually follows the Create link.
    with client.session_transaction() as session:
        session['_flashes'] = [('success', 'Another notification.')]
    assert client.get('/create').status_code == 302
    response = client.get('/create', follow_redirects=True)
    html = response.get_data(as_text=True)
    assert html.count('Please log in to continue.') == 1
    assert html.count('Another notification.') == 1


class _CloseButtonParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.close_buttons = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'button' and 'btn-close' in attrs.get('class', '').split():
            self.close_buttons.append(attrs)


def test_logout_banner_keeps_dismiss_button(auth_client):
    auth_client.get('/')  # Consume the registration welcome banner.
    response = auth_client.post('/logout', follow_redirects=True)
    html = response.get_data(as_text=True)
    assert html.count('You have been logged out.') == 1
    assert 'class="container flash-stack"' in html
    parser = _CloseButtonParser()
    parser.feed(html)
    assert len(parser.close_buttons) == 1
    assert parser.close_buttons[0]['data-bs-dismiss'] == 'alert'
    assert parser.close_buttons[0]['aria-label'] == 'Close'
    assert 'hidden' not in parser.close_buttons[0]
    assert 'style' not in parser.close_buttons[0]


def test_invalid_login_keeps_its_flash(client):
    response = client.post('/login', data={
        'username': 'missing-user', 'password': 'wrong-password',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert response.get_data(as_text=True).count('Invalid username and/or password.') == 1
