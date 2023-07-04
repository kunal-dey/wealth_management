import dash
from dash import html, dcc, callback, Input, Output, State
import requests

dash.register_page(__name__, path='/')

layout = html.Div(children=[
    html.H1(children='This is our Home page'),
    html.Div(children='''
        This is our Home page content.
    '''),
    html.Div(dcc.Input(id='input-on-submit', type='text')),
    html.Button('Submit', id='submit-val', n_clicks=0),
    html.Div(id='container-button-basic',
             children='Enter a value and press submit')
])


@callback(
    Output('container-button-basic', 'children'),
    Input('submit-val', 'n_clicks'),
    State('input-on-submit', 'value')
)
def update_output(n_clicks, value):
    response = requests.get(f"http://127.0.0.1:8080/set?access_token={value}")
    return f'{response.content}'
