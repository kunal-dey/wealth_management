from dash import html, dcc, dash_table, Input, Output, register_page, callback
import sqlite3
from datetime import datetime, timedelta
import pandas as pd

register_page(__name__)

cnx = sqlite3.connect('dash_app/temp/articles.db')
current_date = datetime(2023, 4, 1)
query = "SELECT * FROM articles WHERE"
for date_index in range(6):
    if date_index == 0:
        query += " date ='{0}'".format(str((current_date - timedelta(days=date_index)).date()))
    else:
        query += " or date ='{0}'".format(str((current_date - timedelta(days=date_index)).date()))
df = pd.read_sql_query(query, cnx)
all_options = {date: [newspaper for newspaper in df['newspaper'].unique()] for date in df['date'].unique()}
stock_list_df = pd.read_csv("dash_app/temp/EQUITY_NSE.csv")

layout = html.Div(
    children=[
        html.H1(children='Dashboard'),
        dcc.Dropdown(
            options=list(all_options.keys()),
            value=str(df.date.max()),
            id='date-dropdown'
        ),
        dcc.Dropdown(
            id='newspaper-dropdown'
        ),
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
        html.Br(),
        dcc.Input(id="symbol-input", type="text", placeholder="", style={'marginRight': '10px'}),
        dash_table.DataTable(
            data=df.head().to_dict('records'),
            columns=[{'name': i, 'id': i} for i in df.columns],
            page_action='none',
            fixed_rows={'headers': True},
            style_table={
                'height': '300px',
                'overflowY': 'auto'
            },
            style_cell={'textAlign': 'left'},
            id='news-symbol'
        ),
        dash_table.DataTable(
            data=stock_list_df.head().to_dict('records'),
            columns=[{'name': i, 'id': i} for i in stock_list_df.columns],
            page_action='none',
            fixed_rows={'headers': True},
            style_table={
                'height': '300px',
                'overflowY': 'auto'
            },
            style_cell={'textAlign': 'left'},
            id='symbol'
        ),
    ]
)


@callback(
    Output('newspaper-dropdown', 'options'),
    Input('date-dropdown', 'value'))
def set_cities_options(selected_date):
    return [{'label': i, 'value': i} for i in all_options[selected_date]]


@callback(
    Output('newspaper-dropdown', 'value'),
    Input('newspaper-dropdown', 'options'))
def set_cities_value(available_options):
    return available_options[0]['value']


@callback(
    Output('news-table', 'data'),
    Input('date-dropdown', 'value'),
    Input('newspaper-dropdown', 'value'))
def set_display_children(selected_date, selected_newspaper):
    return df[(df.date == selected_date) & (df.newspaper == selected_newspaper)].to_dict('records')


@callback(
    Output("news-symbol", "data"),
    Input("symbol-input", "value")
)
def update_output(text):
    return df[df['title'].str.lower().str.contains(str(text))].to_dict('records')


@callback(
    Output("symbol", "data"),
    Input("symbol-input", "value")
)
def search_text(text):
    return stock_list_df[stock_list_df['Symbol'].str.lower().str.contains(str(text))].to_dict('records')

