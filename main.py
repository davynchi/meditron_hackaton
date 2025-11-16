from pathlib import Path

import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html

from login import build_login_section, register_login_callbacks
from dashboard import (
    build_patient_options,
    build_dashboard_container,
    register_dashboard_callbacks
)

# --- 1. Data helpers ---

# List of numerical columns for the dropdown selection
numerical_cols = [
    'Hemoglobin', 'Platelet_Count', 'White_Blood_Cells',
    'Red_Blood_Cells', 'MCV', 'MCH', 'MCHC'
]

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




# --- 2. Load data and initialize the Dash App ---
try:
    df, SOURCE_COLUMN_MAP = load_all_datasets(DATA_DIR)
except FileNotFoundError as exc:
    print(f"Error: {exc}")
    exit()

try:
    blood_df = pd.read_csv(DATA_DIR / 'анализ_крови.csv').reset_index(drop=True)
except FileNotFoundError:
    print("Error: 'анализ_крови.csv' not found in the data directory.")
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
        build_login_section(),

        # Dashboard Block (hidden until login)
        build_dashboard_container(
            patient_options,
            blood_parameter_options,
            default_parameter,
            global_scatter_fig
        )
    ]
)

register_login_callbacks(app)
register_dashboard_callbacks(app, df, SOURCE_COLUMN_MAP, blood_df)
# --- 5. Run the Application ---
if __name__ == '__main__':
    print("Dashboard is running on http://127.0.0.1:8050/")
    app.run(host="0.0.0.0", port=8050)
