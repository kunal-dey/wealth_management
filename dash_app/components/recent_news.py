from dash import dash_table
import pandas as pd


def get_news_table(df: pd.DataFrame):
    return dash_table.DataTable(
        df.to_dict('records'),
        [{'name': i, 'id': i} for i in df.columns],
        page_action='none',
        fixed_rows={'headers': True},
        style_table={
            'height': '300px',
            'overflowY': 'auto'
        },
        style_cell={'textAlign': 'left'}
    )
