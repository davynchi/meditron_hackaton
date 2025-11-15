import base64
import io

import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, State, no_update

# --- 1. Data helpers ---

# List of numerical columns for the dropdown selection
numerical_cols = [
    'Hemoglobin', 'Platelet_Count', 'White_Blood_Cells',
    'Red_Blood_Cells', 'MCV', 'MCH', 'MCHC'
]

stat_columns = ['Age', 'Gender'] + numerical_cols


def dataframe_from_records(records):
    """Convert serialized records back into a DataFrame or fallback to default."""
    if not records:
        return pd.DataFrame()
    try:
        df_local = pd.DataFrame(records)
    except Exception:
        return pd.DataFrame()
    return df_local.reset_index(drop=True)


def build_client_options(df_source: pd.DataFrame):
    return [
        {
            'label': f"Client {idx + 1} | {row.get('Gender', 'N/A')} | Age {row.get('Age', 'N/A')}",
            'value': idx
        }
        for idx, row in df_source.iterrows()
    ]


def build_scatter_figure(df_source: pd.DataFrame):
    required_cols = {'Red_Blood_Cells', 'Hemoglobin', 'Gender', 'Age'}
    if not required_cols.issubset(df_source.columns):
        fig = px.scatter(template='plotly_white')
        fig.update_layout(title='Загрузите анализы, чтобы построить диаграмму')
        return fig

    fig = px.scatter(
        df_source,
        x='Red_Blood_Cells',
        y='Hemoglobin',
        color='Gender',
        size='Age',
        hover_data=['Platelet_Count', 'White_Blood_Cells'] if {'Platelet_Count', 'White_Blood_Cells'}.issubset(df_source.columns) else None,
        title='Correlation between Red Blood Cell Count and Hemoglobin',
        template='plotly_white'
    )
    fig.update_xaxes(title=r"$\text{Red Blood Cells } (10^6/\mu L)$")
    fig.update_yaxes(title=r"$\text{Hemoglobin } (g/dL)$")
    return fig


# --- 2. Initialize the Dash App ---
app = Dash(__name__)
server = app.server

# --- 3. Define the Layout ---
app.layout = html.Div(
    style={'backgroundColor': '#f5f5f5', 'padding': '20px', 'minHeight': '100vh'},
    children=[
        dcc.Store(id='auth-store', data={'authorized': False}),
        dcc.Store(id='data-store', data=None),

        # Registration/Login Block
        html.Div(
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
                                'width': '100%',
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
                                'width': '100%',
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
        ),

        # Dashboard Block (hidden until login)
        html.Div(
            id='dashboard-container',
            style={'display': 'none'},
            children=[

                # Header Row
                html.Div(
                    className='row',
                    style={
                        'marginBottom': '20px',
                        'display': 'flex',
                        'justifyContent': 'space-between',
                        'alignItems': 'center',
                        'gap': '20px'
                    },
                    children=[
                        html.Div(
                            style={'textAlign': 'left'},
                            children=[
                                html.H1(
                                    children='Blood Count Parameter Dashboard',
                                    style={'color': '#333333'}
                                ),
                                html.P(
                                    children='Interactive analysis of blood count metrics by Gender and Age.',
                                    style={'color': '#555555'}
                                )
                            ]
                        ),
                        dcc.Upload(
                            id='upload-analyses',
                            children=html.Button(
                                'Загрузить анализы',
                                style={
                                    'padding': '12px 24px',
                                    'backgroundColor': '#ff7f0e',
                                    'color': 'white',
                                    'border': 'none',
                                    'borderRadius': '6px',
                                    'cursor': 'pointer',
                                    'fontSize': '16px'
                                }
                            ),
                            multiple=False,
                            accept='.csv'
                        )
                    ]
                ),

                html.Div(
                    id='dashboard-placeholder',
                    style={
                        'padding': '40px',
                        'backgroundColor': 'white',
                        'borderRadius': '12px',
                        'boxShadow': '2px 2px 10px #aaaaaa',
                        'textAlign': 'center'
                    },
                    children=html.P('Загрузите анализы, чтобы увидеть метрики и графики.', style={'color': '#555555'})
                ),

                html.Div(
                    id='dashboard-content',
                    style={'display': 'none'},
                    children=[
                        # Top Row for Interactive Box Plot
                        html.Div(
                            className='row',
                            style={'display': 'flex', 'marginBottom': '20px'},
                            children=[
                                # Dropdown Menu (on the left)
                                html.Div(
                                    style={'width': '25%', 'padding': '15px', 'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '2px 2px 10px #aaaaaa'},
                                    children=[
                                        html.H3("Select Parameter for Box Plot", style={'textAlign': 'center', 'color': '#1f77b4'}),
                                        dcc.Dropdown(
                                            id='parameter-dropdown',
                                            options=[],
                                            value=None,
                                            clearable=False,
                                            placeholder='Выберите показатель',
                                            style={'marginTop': '10px'}
                                        )
                                    ]
                                ),
                                # Box Plot Graph (on the right)
                                html.Div(
                                    style={'width': '73%', 'marginLeft': '2%', 'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '2px 2px 10px #aaaaaa'},
                                    children=[
                                        dcc.Graph(id='gender-box-plot', style={'height': '450px'})
                                    ]
                                )
                            ]
                        ),

                        # Middle Row for Client Selection
                        html.Div(
                            className='row',
                            style={'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '2px 2px 10px #aaaaaa', 'marginBottom': '20px'},
                            children=[
                                html.H3("Client Statistics", style={'textAlign': 'center', 'color': '#d62728'}),
                                dcc.Dropdown(
                                    id='client-dropdown',
                                    options=[],
                                    value=None,
                                    placeholder='Select a client record',
                                    style={'marginTop': '10px', 'marginBottom': '20px'}
                                ),
                                html.Div(
                                    id='client-statistics',
                                    style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '15px', 'justifyContent': 'center'}
                                )
                            ]
                        ),

                        # Bottom Row for Scatter Plot
                        html.Div(
                            className='row',
                            style={'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '2px 2px 10px #aaaaaa'},
                            children=[
                                html.H3("Red Blood Cells vs. Hemoglobin by Age and Gender", style={'textAlign': 'center', 'color': '#2ca02c'}),
                                dcc.Graph(
                                    id='rbc-hgb-scatter',
                                    figure=build_scatter_figure(pd.DataFrame()),
                                    style={'height': '500px'}
                                )
                            ]
                        )
                    ]
                )
            ]
        )
    ]
)

# --- 4. Define Callbacks for Interactivity ---
@app.callback(
    Output('auth-store', 'data'),
    Output('login-feedback', 'children'),
    Input('login-button', 'n_clicks'),
    State('login-input', 'value'),
    State('password-input', 'value'),
    prevent_initial_call=True
)
def handle_login(n_clicks, username, password):
    """Very simple auth stub: require both fields and then unlock dashboard."""
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
    Output('dashboard-content', 'style'),
    Output('dashboard-placeholder', 'style'),
    Input('data-store', 'data')
)
def toggle_dashboard_content(data_records):
    has_data = bool(data_records)

    content_style = {'display': 'block'} if has_data else {'display': 'none'}
    placeholder_style = {
        'padding': '40px',
        'backgroundColor': 'white',
        'borderRadius': '12px',
        'boxShadow': '2px 2px 10px #aaaaaa',
        'textAlign': 'center'
    }
    if has_data:
        placeholder_style['display'] = 'none'
    return content_style, placeholder_style


@app.callback(
    Output('data-store', 'data'),
    Input('upload-analyses', 'contents'),
    State('upload-analyses', 'filename'),
    prevent_initial_call=True
)
def handle_file_upload(contents, filename):
    """Parse the uploaded CSV and store it for downstream callbacks."""
    if contents is None:
        return no_update

    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df_uploaded = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        df_uploaded = df_uploaded.reset_index(drop=True)
    except Exception:
        return no_update

    return df_uploaded.to_dict('records')


@app.callback(
    Output('parameter-dropdown', 'options'),
    Output('parameter-dropdown', 'value'),
    Input('data-store', 'data')
)
def refresh_parameter_dropdown(data_records):
    df_local = dataframe_from_records(data_records)
    available = [col for col in numerical_cols if col in df_local.columns]
    options = [{'label': col.replace('_', ' '), 'value': col} for col in available]
    value = available[0] if available else None
    return options, value


@app.callback(
    Output('gender-box-plot', 'figure'),
    Input('parameter-dropdown', 'value'),
    Input('data-store', 'data')
)
def update_box_plot(selected_parameter, data_records):
    """Generates the box plot based on the dropdown selection."""
    df_local = dataframe_from_records(data_records)

    if not selected_parameter or selected_parameter not in df_local.columns:
        fig = px.box(template='plotly_white')
        fig.update_layout(title='Параметр недоступен в выбранном файле')
        return fig

    if 'Gender' not in df_local.columns:
        fig = px.box(template='plotly_white')
        fig.update_layout(title='Пол (Gender) отсутствует в наборе данных')
        return fig

    fig = px.box(
        df_local,
        x='Gender',
        y=selected_parameter,
        color='Gender',
        notched=True,
        points='suspectedoutliers',
        title=f'Distribution of {selected_parameter.replace("_", " ")} by Gender',
        labels={selected_parameter: selected_parameter.replace("_", " ")},
        template='plotly_white'
    )
    fig.update_layout(
        margin={'l': 40, 'b': 40, 't': 40, 'r': 10},
        plot_bgcolor='white',
        paper_bgcolor='white',
        showlegend=False
    )
    return fig


@app.callback(
    Output('client-statistics', 'children'),
    Input('client-dropdown', 'value'),
    Input('data-store', 'data')
)
def update_client_statistics(selected_client, data_records):
    """Show a card-based summary for the selected client."""
    df_local = dataframe_from_records(data_records)

    if selected_client is None or selected_client not in df_local.index:
        return html.P('Select a client to view detailed statistics.', style={'color': '#555555'})

    client_data = df_local.loc[selected_client]
    cards = []
    card_style = {
        'border': '1px solid #e0e0e0',
        'borderRadius': '8px',
        'padding': '15px',
        'width': '150px',
        'textAlign': 'center',
        'backgroundColor': '#fafafa',
        'boxShadow': '1px 1px 5px #dddddd'
    }

    for column in stat_columns:
        value = client_data[column] if column in client_data else 'N/A'
        if pd.isna(value):
            value_display = 'N/A'
        elif isinstance(value, float):
            value_display = f"{value:.2f}"
        else:
            value_display = str(value)

        cards.append(
            html.Div([
                html.H5(column.replace('_', ' '), style={'marginBottom': '5px', 'color': '#333333'}),
                html.P(value_display, style={'color': '#1f77b4', 'fontWeight': 'bold', 'margin': 0})
            ], style=card_style)
        )

    return cards


@app.callback(
    Output('client-dropdown', 'options'),
    Output('client-dropdown', 'value'),
    Input('data-store', 'data')
)
def refresh_client_dropdown(data_records):
    df_local = dataframe_from_records(data_records)
    options = build_client_options(df_local)
    value = options[0]['value'] if options else None
    return options, value


@app.callback(
    Output('rbc-hgb-scatter', 'figure'),
    Input('data-store', 'data')
)
def update_scatter(data_records):
    df_local = dataframe_from_records(data_records)
    return build_scatter_figure(df_local)

# --- 5. Run the Application ---
if __name__ == '__main__':
    print("Dashboard is running on http://127.0.0.1:8050/")
    app.run(debug=True)
