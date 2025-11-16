import pandas as pd
import plotly.express as px
from dash import dcc, html, Input, Output


CARD_STYLE = {
    'border': '1px solid #e0e0e0',
    'borderRadius': '14px',
    'padding': '15px',
    'minWidth': '140px',
    'textAlign': 'center',
    'backgroundColor': '#fafafa',
    'boxShadow': '1px 1px 6px rgba(0, 0, 0, 0.1)'
}


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


def build_patient_result_sections(patient_df: pd.DataFrame, source_column_map):
    if patient_df.empty:
        return html.P('Нет данных по выбранному пациенту.', style={'color': '#555555'})

    sections = []
    for source_name, subset in patient_df.groupby('Source_File'):
        record = subset.iloc[-1]
        source_columns = source_column_map.get(source_name, subset.columns.tolist())

        priority_cols = [col for col in ['Age', 'Gender'] if col in source_columns]
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
                style={
                    'padding': '20px',
                    'border': '1px solid #e0e0e0',
                    'borderRadius': '12px',
                    'backgroundColor': 'white',
                    'boxShadow': '2px 2px 8px rgba(0,0,0,0.1)'
                },
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


def build_dashboard_container(patient_options, blood_parameter_options, default_parameter, global_scatter_fig):
    return html.Div(
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
                    html.Div(
                        className='row',
                        style={'marginBottom': '20px', 'textAlign': 'center'},
                        children=[
                            html.H1('Blood Count Parameter Dashboard', style={'color': '#333333'}),
                            html.P('Interactive analysis of blood count metrics by Gender and Age.', style={'color': '#555555'})
                        ]
                    ),
                    html.Div(id='patient-results', style={'marginBottom': '20px'}),
                    html.Div(
                        className='row',
                        style={'display': 'flex', 'marginBottom': '20px'},
                        children=[
                            html.Div(
                                style={'width': '25%', 'padding': '15px', 'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '2px 2px 10px #aaaaaa'},
                                children=[
                                    html.H3('Select Parameter for Box Plot', style={'textAlign': 'center', 'color': '#1f77b4'}),
                                    dcc.Dropdown(
                                        id='parameter-dropdown',
                                        options=blood_parameter_options,
                                        value=default_parameter,
                                        clearable=False,
                                        style={'marginTop': '10px'}
                                    )
                                ]
                            ),
                            html.Div(
                                style={'width': '73%', 'marginLeft': '2%', 'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '2px 2px 10px #aaaaaa'},
                                children=[
                                    dcc.Graph(id='gender-box-plot', style={'height': '450px'})
                                ]
                            )
                        ]
                    ),
                    html.Div(
                        className='row',
                        style={'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '2px 2px 10px #aaaaaa'},
                        children=[
                            html.H3('Red Blood Cells vs. Hemoglobin by Age and Gender', style={'textAlign': 'center', 'color': '#2ca02c'}),
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
        Output('gender-box-plot', 'figure'),
        Input('parameter-dropdown', 'value')
    )
    def update_box_plot(selected_parameter):
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

    return app
