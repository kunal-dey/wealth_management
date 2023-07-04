import pandas as pd
from dash import html, dcc, dash_table, register_page

register_page(__name__)

df = pd.read_csv("dash_app/temp/stock_prediction.csv")

layout = html.Div(
    children=[
        html.H1(children='List of predicted stocks'),
        dash_table.DataTable(
            data=df.to_dict('records'),
            columns=[{'name': i, 'id': i} for i in df.columns],
            page_action='none',
            fixed_rows={'headers': True},
            style_table={
                'height': '300px',
                'overflowY': 'auto'
            },
            style_cell={'textAlign': 'left'},
            id='news-table'
        ),
    ]
)
