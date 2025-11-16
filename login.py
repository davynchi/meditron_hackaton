from dash import dcc, html, Input, Output, State, no_update


def build_login_section():
    return html.Div(
        id='login-container',
        style={
            'display': 'flex',
            'alignItems': 'center',
            'justifyContent': 'center',
            'minHeight': '80vh'
        },
        children=[
            html.Div(
                style={
                    'width': '100%',
                    'maxWidth': '420px',
                    'padding': '30px',
                    'backgroundColor': 'white',
                    'borderRadius': '12px',
                    'boxShadow': '2px 2px 12px rgba(0, 0, 0, 0.1)'
                },
                children=[
                    html.H2('Вход в систему визуализации', style={'textAlign': 'center', 'color': '#333333'}),
                    html.P(
                        'Введите логин и пароль, чтобы открыть панель мониторинга лаборатории.',
                        style={'textAlign': 'center', 'color': '#555555'}
                    ),
                    dcc.Input(
                        id='login-input',
                        placeholder='Логин',
                        type='text',
                        style={
                            'width': 'calc(100% - 2px)',
                            'padding': '12px',
                            'marginTop': '15px',
                            'border': '1px solid #cccccc',
                            'borderRadius': '6px'
                        }
                    ),
                    dcc.Input(
                        id='password-input',
                        placeholder='Пароль',
                        type='password',
                        style={
                            'width': 'calc(100% - 2px)',
                            'padding': '12px',
                            'marginTop': '10px',
                            'border': '1px solid #cccccc',
                            'borderRadius': '6px'
                        }
                    ),
                    html.Button(
                        'Войти',
                        id='login-button',
                        n_clicks=0,
                        style={
                            'width': '100%',
                            'marginTop': '20px',
                            'padding': '12px',
                            'backgroundColor': '#1f77b4',
                            'color': 'white',
                            'border': 'none',
                            'borderRadius': '6px',
                            'fontSize': '16px',
                            'cursor': 'pointer'
                        }
                    ),
                    html.Div(
                        id='login-feedback',
                        style={'marginTop': '10px', 'color': '#d62728', 'textAlign': 'center'}
                    )
                ]
            )
        ]
    )


def register_login_callbacks(app):
    @app.callback(
        Output('auth-store', 'data'),
        Output('login-feedback', 'children'),
        Input('login-button', 'n_clicks'),
        State('login-input', 'value'),
        State('password-input', 'value'),
        prevent_initial_call=True
    )
    def handle_login(n_clicks, username, password):
        if not username or not password:
            return no_update, 'Введите логин и пароль.'

        return {'authorized': True, 'username': username}, ''

    @app.callback(
        Output('login-container', 'style'),
        Output('dashboard-container', 'style'),
        Input('auth-store', 'data')
    )
    def toggle_pages(auth_data):
        is_authorized = auth_data.get('authorized') if isinstance(auth_data, dict) else False

        login_style = {
            'alignItems': 'center',
            'justifyContent': 'center',
            'minHeight': '80vh',
            'display': 'none' if is_authorized else 'flex'
        }
        dashboard_style = {'display': 'block' if is_authorized else 'none'}
        return login_style, dashboard_style

    @app.callback(
        Output('auth-store', 'data', allow_duplicate=True),
        Input('logout-button', 'n_clicks'),
        prevent_initial_call=True
    )
    def handle_logout(n_clicks):
        if n_clicks:
            return {'authorized': False}
        return no_update

    return app
