from pathlib import Path

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

CARD_STYLE = {
    'border': '1px solid #e0e0e0',
    'borderRadius': '14px',
    'padding': '15px',
    'minWidth': '140px',
    'textAlign': 'center',
    'backgroundColor': '#fafafa',
    'boxShadow': '1px 1px 6px rgba(0,0,0,0.1)'
}

DATA_DIR = Path('data')
SOURCE_COLUMN_MAP = {}


def load_all_datasets(data_dir: Path):
    frames = []
    column_map = {}
    if data_dir.exists():
        for csv_file in sorted(data_dir.glob('*.csv')):
            try:
                df_local = pd.read_csv(csv_file)
            except Exception:
                continue

            column_map[csv_file.name] = df_local.columns.tolist()
            df_local['Source_File'] = csv_file.name
            frames.append(df_local)

    if not frames:
        raise FileNotFoundError("No CSV files found inside the 'data' directory.")

    combined = pd.concat(frames, ignore_index=True)
    return combined.reset_index(drop=True), column_map


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


def format_value(value):
    if pd.isna(value):
        return 'N/A'
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def build_patient_options(df_source: pd.DataFrame):
    unique_patients = df_source[['Patient_Key', 'Age', 'Gender']].drop_duplicates('Patient_Key')
    options = []
    for _, row in unique_patients.iterrows():
        age = row.get('Age', 'N/A')
        gender = str(row.get('Gender', 'N/A')).title()
        options.append({
            'label': f"Пациент: возраст {age}, пол {gender}",
            'value': row['Patient_Key']
        })
    return options


def build_patient_result_sections(patient_df: pd.DataFrame):
    if patient_df.empty:
        return html.P('Нет данных по выбранному пациенту.', style={'color': '#555555'})

    sections = []
    for source_name, subset in patient_df.groupby('Source_File'):
        record = subset.iloc[-1]
        source_columns = SOURCE_COLUMN_MAP.get(source_name, subset.columns.tolist())

        priority_cols = []
        for col in ['Age', 'Gender']:
            if col in source_columns and col not in priority_cols:
                priority_cols.append(col)

        remaining_cols = [col for col in source_columns if col not in priority_cols]
        display_columns = priority_cols + remaining_cols

        cards = []
        for column in display_columns:
            if column not in subset.columns:
                continue
            cards.append(
                html.Div([
                    html.H5(column.replace('_', ' '), style={'marginBottom': '4px', 'color': '#7f3f00'}),
                    html.P(format_value(record[column]), style={'color': '#1f77b4', 'fontWeight': 'bold', 'margin': 0})
                ], style=CARD_STYLE)
            )

        sections.append(
            html.Div(
                style={'padding': '20px', 'border': '1px solid #e0e0e0', 'borderRadius': '12px', 'backgroundColor': 'white', 'boxShadow': '2px 2px 8px rgba(0,0,0,0.1)'},
                children=[
                    html.H4(f"Источник: {source_name}", style={'color': '#1f77b4', 'marginBottom': '15px'}),
                    html.Div(cards, style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '15px'})
                ]
            )
        )

    return html.Div(
        style={'display': 'flex', 'flexDirection': 'column', 'gap': '20px'},
        children=sections
    )


# --- 2. Load data and initialize the Dash App ---
try:
    df, SOURCE_COLUMN_MAP = load_all_datasets(DATA_DIR)
except FileNotFoundError as exc:
    print(f"Error: {exc}")
    exit()

try:
    blood_df = pd.read_csv(DATA_DIR / 'blood_count_dataset.csv').reset_index(drop=True)
except FileNotFoundError:
    print("Error: 'blood_count_dataset.csv' not found in the data directory.")
    exit()

df['Gender'] = df['Gender'].astype(str)
df['Gender_Norm'] = df['Gender'].str.lower().str.strip()
df['Age_Str'] = df['Age'].astype(str)
df['Patient_Key'] = df['Age_Str'] + '|' + df['Gender_Norm']

patient_options = build_patient_options(df)
blood_parameter_options = [{'label': col.replace('_', ' '), 'value': col} for col in numerical_cols if col in blood_df.columns]
default_parameter = blood_parameter_options[0]['value'] if blood_parameter_options else None
global_scatter_fig = build_scatter_figure(blood_df)

# initialize Dash
app = Dash(__name__)
server = app.server

# --- 3. Define the Layout ---
app.layout = html.Div(
    style={'backgroundColor': '#f5f5f5', 'padding': '20px', 'minHeight': '100vh'},
    children=[
        dcc.Store(id='auth-store', data={'authorized': False}),
        dcc.Store(id='patient-data-store', data=[]),

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

                html.Div(
                    style={'marginBottom': '20px', 'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '10px', 'boxShadow': '2px 2px 10px #aaaaaa'},
                    children=[
                        html.H2('Выберите пациента', style={'color': '#1f77b4'}),
                        dcc.Dropdown(
                            id='patient-dropdown',
                            options=patient_options,
                            placeholder='Выберите уникальную комбинацию возраста и пола',
                            value=None,
                            style={'marginTop': '10px'}
                        )
                    ]
                ),

                html.Div(
                    id='visual-section',
                    style={'display': 'none'},
                    children=[
                        # Header Row
                        html.Div(
                            className='row',
                            style={
                                'marginBottom': '20px',
                                'textAlign': 'center'
                            },
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

                        html.Div(
                            id='patient-results',
                            style={'marginBottom': '20px'}
                        ),

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
                                            options=blood_parameter_options,
                                            value=default_parameter,
                                            clearable=False,
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

                        # Patient Statistics
                        html.Div(
                            className='row',
                            style={'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '2px 2px 10px #aaaaaa', 'marginBottom': '20px'},
                            children=[
                                html.H3("Patient Statistics", style={'textAlign': 'center', 'color': '#d62728'}),
                                html.Div(
                                    id='patient-statistics',
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
                                    figure=global_scatter_fig,
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
    Output('patient-data-store', 'data'),
    Output('patient-results', 'children'),
    Output('visual-section', 'style'),
    Input('patient-dropdown', 'value')
)
def handle_patient_selection(patient_key):
    if not patient_key:
        return [], html.Div(), {'display': 'none'}

    patient_df = df[df['Patient_Key'] == patient_key]
    if patient_df.empty:
        return [], html.P('Нет данных по выбранному пациенту.', style={'color': '#555555'}), {'display': 'none'}

    result_sections = build_patient_result_sections(patient_df)
    return patient_df.to_dict('records'), result_sections, {'display': 'block'}


@app.callback(
    Output('gender-box-plot', 'figure'),
    Input('parameter-dropdown', 'value')
)
def update_box_plot(selected_parameter):
    """Generates the box plot based on the dropdown selection."""
    if not selected_parameter or selected_parameter not in blood_df.columns:
        fig = px.box(template='plotly_white')
        fig.update_layout(title='Параметр недоступен в текущем наборе данных')
        return fig

    if 'Gender' not in blood_df.columns:
        fig = px.box(template='plotly_white')
        fig.update_layout(title='Пол (Gender) отсутствует в наборе данных')
        return fig

    fig = px.box(
        blood_df,
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
    Output('patient-statistics', 'children'),
    Input('patient-data-store', 'data')
)
def update_patient_statistics(patient_records):
    patient_df = pd.DataFrame(patient_records)
    if patient_df.empty:
        return html.P('Выберите пациента, чтобы увидеть статистику.', style={'color': '#555555'})

    cards = []

    for column in stat_columns:
        if column not in patient_df.columns:
            continue
        if column in numerical_cols:
            value = patient_df[column].mean()
        else:
            value = patient_df[column].iloc[0]

        cards.append(
            html.Div([
                html.H5(column.replace('_', ' '), style={'marginBottom': '5px', 'color': '#7f3f00'}),
                html.P(format_value(value), style={'color': '#1f77b4', 'fontWeight': 'bold', 'margin': 0})
            ], style=CARD_STYLE)
        )

    return cards



# --- 5. Run the Application ---
if __name__ == '__main__':
    print("Dashboard is running on http://127.0.0.1:8050/")
    app.run(debug=True)
