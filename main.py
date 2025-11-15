import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output

# --- 1. Load the Data ---
# Load your uploaded CSV file
try:
    df = pd.read_csv("blood_count_dataset.csv")
except FileNotFoundError:
    print("Error: 'blood_count_dataset.csv' not found. Please ensure it is in the same directory.")
    exit()

df = df.reset_index(drop=True)

# Build dropdown-friendly client labels so the UI can reference individual records
client_options = [
    {
        'label': f"Client {idx + 1} | {row['Gender']} | Age {row['Age']}",
        'value': idx
    }
    for idx, row in df.reset_index(drop=True).iterrows()
]

# List of numerical columns for the dropdown selection
numerical_cols = [
    'Hemoglobin', 'Platelet_Count', 'White_Blood_Cells',
    'Red_Blood_Cells', 'MCV', 'MCH', 'MCHC'
]

stat_columns = ['Age', 'Gender'] + numerical_cols

# --- 2. Initialize the Dash App ---
app = Dash(__name__)
server = app.server

# --- 3. Define the Layout ---
app.layout = html.Div(style={'backgroundColor': '#f5f5f5', 'padding': '20px'}, children=[

    # Header Row
    html.Div(
        className='row',
        style={'marginBottom': '20px', 'textAlign': 'center'},
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
                        options=[{'label': col.replace('_', ' '), 'value': col} for col in numerical_cols],
                        value='Hemoglobin',  # Default selected value
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

    # Middle Row for Client Selection
    html.Div(
        className='row',
        style={'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '8px', 'boxShadow': '2px 2px 10px #aaaaaa', 'marginBottom': '20px'},
        children=[
            html.H3("Client Statistics", style={'textAlign': 'center', 'color': '#d62728'}),
            dcc.Dropdown(
                id='client-dropdown',
                options=client_options,
                value=client_options[0]['value'] if client_options else None,
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
                figure=px.scatter(
                    df,
                    x='Red_Blood_Cells',
                    y='Hemoglobin',
                    color='Gender',
                    size='Age',
                    hover_data=['Platelet_Count', 'White_Blood_Cells'],
                    title='Correlation between Red Blood Cell Count and Hemoglobin',
                    labels={
                        "Red_Blood_Cells": r"Red Blood Cells ($10^6/\mu L$)",
                        "Hemoglobin": "Hemoglobin (g/dL)"
                    },
                    template='plotly_white'
                ),
                style={'height': '500px'}
            )
        ]
    )
])

# --- 4. Define Callbacks for Interactivity ---
@app.callback(
    Output('gender-box-plot', 'figure'),
    [Input('parameter-dropdown', 'value')]
)
def update_box_plot(selected_parameter):
    """Generates the box plot based on the dropdown selection."""
    fig = px.box(
        df,
        x='Gender',
        y=selected_parameter,
        color='Gender',
        notched=True,
        points='suspectedoutliers', # Show outliers
        title=f'Distribution of {selected_parameter.replace("_", " ")} by Gender',
        labels={selected_parameter: selected_parameter.replace("_", " ")},
        template='plotly_white'
    )
    # Customize layout for better appearance
    fig.update_layout(
        margin={'l': 40, 'b': 40, 't': 40, 'r': 10},
        plot_bgcolor='white',
        paper_bgcolor='white',
        showlegend=False
    )
    return fig


@app.callback(
    Output('client-statistics', 'children'),
    [Input('client-dropdown', 'value')]
)
def update_client_statistics(selected_client):
    """Show a card-based summary for the selected client."""
    if selected_client is None or selected_client not in df.index:
        return html.P('Select a client to view detailed statistics.', style={'color': '#555555'})

    client_data = df.loc[selected_client]
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
        value = client_data[column]
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

# --- 5. Run the Application ---
if __name__ == '__main__':
    print("Dashboard is running on http://127.0.0.1:8050/")
    app.run(debug=True)
