import pandas as pd
import plotly.express as px
from dash import dcc, html, Input, Output, State, ALL, no_update, ctx


CARD_STYLE = {
    'border': '1px solid #e0e0e0',
    'borderRadius': '14px',
    'padding': '15px',
    'minWidth': '140px',
    'textAlign': 'center',
    'backgroundColor': '#fafafa',
    'boxShadow': '1px 1px 6px rgba(0, 0, 0, 0.1)'
}

BLOOD_FILES = {'анализ_крови.csv', 'анализ_крови.xlsx'}


def _to_float(value):
    if value is None or value == '':
        return None
    try:
        return float(str(value).replace(',', '.'))
    except ValueError:
        return None


def build_range_gauge(row, value_key, min_key, max_key, title):
    value = _to_float(row.get(value_key))
    min_norm = _to_float(row.get(min_key))
    max_norm = _to_float(row.get(max_key))

    if value is None or min_norm is None or max_norm is None or max_norm <= min_norm:
        return html.Div(f'Нет данных по показателю {title}', style={'color': '#777', 'marginTop': '10px'})

    if value <= min_norm:
        position = 0
    elif value >= max_norm:
        position = 100
    else:
        ratio = (value - min_norm) / (max_norm - min_norm)
        position = 33.3 + ratio * 33.4  # place within middle third

    bar_style = {
        'position': 'relative',
        'width': '100%',
        'height': '36px',
        'borderRadius': '18px',
        'background': 'linear-gradient(90deg, #ffb347 0%, #7fff8a 50%, #ffb347 100%)'
    }
    marker_style = {
        'position': 'absolute',
        'top': '50%',
        'left': f'{position:.2f}%',
        'transform': 'translate(-50%, -50%)',
        'width': '32px',
        'height': '32px',
        'borderRadius': '50%',
        'border': '2px solid #d62728',
        'backgroundColor': 'white',
        'display': 'flex',
        'alignItems': 'center',
        'justifyContent': 'center',
        'fontWeight': 'bold',
        'zIndex': 2
    }
    stick_style = lambda offset: {
        'position': 'absolute',
        'top': 0,
        'left': offset,
        'transform': 'translateX(-50%)',
        'width': '2px',
        'height': '100%',
        'backgroundColor': 'rgba(255, 255, 255, 0.8)',
        'zIndex': 1
    }

    border_labels = html.Div(
        [
            html.Span(
                f"{min_norm:.1f}",
                style={
                    'position': 'absolute',
                    'left': '33.3%',
                    'transform': 'translate(-50%, 0)',
                    'color': '#555'
                }
            ),
            html.Span(
                f"{max_norm:.1f}",
                style={
                    'position': 'absolute',
                    'left': '66.6%',
                    'transform': 'translate(-50%, 0)',
                    'color': '#555'
                }
            )
        ],
        style={'position': 'relative', 'height': '24px', 'marginTop': '6px'}
    )

    return html.Div([
        html.Div(title, style={'color': '#d62728', 'fontWeight': 'bold', 'marginBottom': '6px'}),
        html.Div(
            [
                html.Div(
                    [
                        html.Div('', style=stick_style('33.3%')),
                        html.Div('', style=stick_style('66.6%')),
                        html.Div(f"{value:.1f}", style=marker_style)
                    ],
                    style=bar_style
                ),
                border_labels
            ]
        )
    ], style={'marginTop': '10px', 'marginBottom': '10px'})


def build_hemoglobin_gauge(row):
    return build_range_gauge(row, 'Гемоглобин', 'Гемоглобин мин норма', 'Гемоглобин макс норма', 'Гемоглобин')


def build_platelet_gauge(row):
    return build_range_gauge(row, 'Тромбоциты', 'Тромбоциты мин норма', 'Тромбоциты макс норма', 'Тромбоциты')


def format_value(value):
    if pd.isna(value):
        return 'N/A'
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def build_patient_options(df_source: pd.DataFrame):
    unique_patients = df_source['ID'].drop_duplicates()
    options = []
    for idx in unique_patients:
        options.append({
            'label': f"Пациент: ID {idx}",
            'value': idx
        })
    return options


def build_patient_result_sections(patient_df: pd.DataFrame, source_column_map):
    if patient_df.empty:
        return html.P('Нет данных по выбранному пациенту.', style={'color': '#555555'})

    date_column = 'Дата' if 'Дата' in patient_df.columns else ('Date' if 'Date' in patient_df.columns else None)
    if date_column:
        patient_df = patient_df.sort_values(by=date_column, ascending=False)

    sections = []
    for source_name, subset in patient_df.groupby('Source_File'):
        source_columns = source_column_map.get(source_name, subset.columns.tolist())
        display_columns = [
            col for col in source_columns
            if col not in (
                'ID', 'Дата', 'Date', 'Имя', 'Пол',
                'Гемоглобин', 'Гемоглобин мин норма', 'Гемоглобин макс норма',
                'Тромбоциты', 'Тромбоциты мин норма', 'Тромбоциты макс норма'
            )
        ]

        rows = []
        header_name = subset.iloc[0].get('Имя', 'Имя неизвестно')
        header_gender = subset.iloc[0].get('Пол', 'Пол неизвестен')
        for _, row in subset.iterrows():
            cards = []
            for column in display_columns:
                if column not in subset.columns:
                    continue
                cards.append(
                    html.Button(
                        html.Div([
                            html.H5(column.replace('_', ' '), style={'marginBottom': '4px', 'color': '#7f3f00'}),
                            html.P(format_value(row[column]), style={'color': '#1f77b4', 'fontWeight': 'bold', 'margin': 0})
                        ], style=CARD_STYLE),
                        id={'type': 'metric-card', 'metric': column},
                        n_clicks=0,
                        style={'background': 'transparent', 'border': 'none', 'padding': 0, 'cursor': 'pointer'}
                    )
                )

            date_value = row.get('Дата') or row.get('Date') or 'N/A'
            detail_children = [html.Summary(f"{source_name} — {date_value}")]
            if source_name in BLOOD_FILES:
                detail_children.append(build_hemoglobin_gauge(row))
                detail_children.append(build_platelet_gauge(row))
            detail_children.append(
                html.Div(cards, style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '15px', 'marginTop': '10px'})
            )

            rows.append(
                html.Details(
                    open=True,
                    style={'marginBottom': '12px', 'border': '1px solid #e0e0e0', 'borderRadius': '8px', 'padding': '10px'},
                    children=detail_children
                )
            )

        sections.append(
            html.Div(
                style={
                    'padding': '20px',
                    'border': '1px solid #e0e0e0',
                    'borderRadius': '12px',
                    'backgroundColor': 'white',
                    'boxShadow': '2px 2px 8px rgba(0,0,0,0.1)'
                },
                children=[
                    html.H4(
                        f"Источник: {source_name}",
                        style={'color': '#1f77b4', 'marginBottom': '5px'}
                    ),
                    html.P(
                        f"{header_name} — {header_gender}",
                        style={'color': '#555555', 'marginBottom': '15px'}
                    ),
                    html.Div(rows, style={'display': 'flex', 'flexDirection': 'column', 'gap': '10px'})
                ]
            )
        )

    return html.Div(
        style={'display': 'flex', 'flexDirection': 'column', 'gap': '20px'},
        children=sections
    )


def build_dashboard_container(patient_options, global_scatter_fig):
    return html.Div(
        id='dashboard-container',
        style={'display': 'none'},
        children=[
            html.Div(
                style={
                    'marginBottom': '20px',
                    'backgroundColor': 'white',
                    'padding': '20px',
                    'borderRadius': '10px',
                    'boxShadow': '2px 2px 10px #aaaaaa',
                    'display': 'flex',
                    'flexWrap': 'wrap',
                    'gap': '20px',
                    'alignItems': 'center',
                    'justifyContent': 'space-between'
                },
                children=[
                    html.Div(
                        style={'flex': '1 1 300px'},
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
                    html.Button(
                        'Выйти из системы',
                        id='logout-button',
                        n_clicks=0,
                        style={
                            'backgroundColor': '#d62728',
                            'color': 'white',
                            'border': 'none',
                            'borderRadius': '6px',
                            'padding': '12px 20px',
                            'fontSize': '16px',
                            'cursor': 'pointer'
                        }
                    )
                ]
            ),

            html.Div(
                id='visual-section',
                style={'display': 'none'},
                children=[
                    html.Div(
                        className='row',
                        style={'marginBottom': '20px', 'textAlign': 'center'},
                        children=[
                            html.H1('Дашборд по пациенту', style={'color': '#FFFFFF'}),
                            html.P('Интерактивное отображение анализов пациента', style={'color': '#FFFFFF'})
                        ]
                    ),
                    html.Div(id='patient-results', style={'marginBottom': '20px'}),
                    html.Div(
                        className='row',
                        style={'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '2px 2px 10px #aaaaaa', 'marginBottom': '20px'},
                        children=[
                            html.H3(id='boxplot-title', style={'textAlign': 'center', 'color': '#1f77b4', 'width': '100%'}),
                            dcc.Graph(id='gender-box-plot', style={'height': '450px', 'width': '100%'})
                        ]
                    ),
                    html.Div(
                        className='row',
                        style={'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '2px 2px 10px #aaaaaa'},
                        children=[
                            html.H3('Эритроциты vs. Гемоглобин by Возраст and Пол', style={'textAlign': 'center', 'color': '#2ca02c'}),
                            dcc.Graph(id='rbc-hgb-scatter', figure=global_scatter_fig, style={'height': '500px'})
                        ]
                    )
                ]
            )
        ]
    )


def register_dashboard_callbacks(app, df, source_column_map, blood_df):
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

        result_sections = build_patient_result_sections(patient_df, source_column_map)
        return patient_df.to_dict('records'), result_sections, {'display': 'block'}

    @app.callback(
        Output('selected-metric', 'data'),
        Input({'type': 'metric-card', 'metric': ALL}, 'n_clicks'),
        State('selected-metric', 'data'),
        prevent_initial_call=True
    )
    def set_selected_metric(clicks, current_metric):
        if not ctx.triggered_id:
            return no_update
        metric = ctx.triggered_id.get('metric') if isinstance(ctx.triggered_id, dict) else None
        if metric and metric in blood_df.columns:
            return metric
        return current_metric

    @app.callback(
        Output('gender-box-plot', 'figure'),
        Output('boxplot-title', 'children'),
        Input('selected-metric', 'data')
    )
    def update_box_plot(selected_parameter):
        if not selected_parameter or selected_parameter not in blood_df.columns:
            fig = px.box(template='plotly_white')
            fig.update_layout(title='Параметр недоступен в текущем наборе данных')
            return fig, 'Выберите показатель, кликая по карточкам пациента — boxplot'

        if 'Пол' not in blood_df.columns:
            fig = px.box(template='plotly_white')
            fig.update_layout(title='Пол (Пол) отсутствует в наборе данных')
            return fig, 'Boxplot недоступен: нет колонки Пол'

        fig = px.box(
            blood_df,
            x='Пол',
            y=selected_parameter,
            color='Пол',
            notched=True,
            points='suspectedoutliers',
            title=f'Distribution of {selected_parameter.replace("_", " ")} by Пол',
            labels={selected_parameter: selected_parameter.replace("_", " ")},
            template='plotly_white'
        )
        fig.update_layout(
            margin={'l': 40, 'b': 40, 't': 40, 'r': 10},
            plot_bgcolor='white',
            paper_bgcolor='white',
            showlegend=False
        )
        header = f"Boxplot: {selected_parameter.replace('_', ' ')}"
        return fig, header

    return app
