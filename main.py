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


def read_tabular_file(file_path: Path) -> pd.DataFrame:
    if file_path.suffix.lower() == '.xlsx':
        return pd.read_excel(file_path)
    return pd.read_csv(file_path)


def load_all_datasets(data_dir: Path):
    frames = []
    column_map = {}
    if data_dir.exists():
        for pattern in ('*.csv', '*.xlsx'):
            for file_path in sorted(data_dir.glob(pattern)):
                try:
                    df_local = read_tabular_file(file_path)
                except Exception:
                    continue

                column_map[file_path.name] = df_local.columns.tolist()
                df_local['Source_File'] = file_path.name
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

blood_df = None
for base_name in ('blood_count_dataset', 'анализ_крови'):
    for ext in ('.csv', '.xlsx'):
        candidate = DATA_DIR / f"{base_name}{ext}"
        if candidate.exists():
            blood_df = read_tabular_file(candidate).reset_index(drop=True)
            break
    if blood_df is not None:
        break

if blood_df is None:
    print("Error: 'blood_count_dataset.(csv|xlsx)' or 'анализ_крови.(csv|xlsx)' not found in the data directory.")
    exit()

df['Gender'] = df['Gender'].astype(str)
df['Gender_Norm'] = df['Gender'].str.lower().str.strip()
df['Age_Str'] = df['Age'].astype(str)
df['Patient_Key'] = df['Age_Str'] + '|' + df['Gender_Norm']

patient_options = build_patient_options(df)
if 'Hemoglobin' in blood_df.columns:
    default_metric = 'Hemoglobin'
else:
    numeric_candidates = [col for col in numerical_cols if col in blood_df.columns]
    default_metric = numeric_candidates[0] if numeric_candidates else blood_df.columns[0]
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
        dcc.Store(id='selected-metric', data=default_metric),

        # Registration/Login Block
        build_login_section(),

        # Dashboard Block (hidden until login)
        build_dashboard_container(
            patient_options,
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
