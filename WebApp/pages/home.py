import dash
from dash import html, dcc, callback, Input, Output

dash.register_page(__name__, path="/")

from core import api

layout = html.Div([
  html.Div([
    html.H1("Spacecraft Simulation Environment")
  ])
], className="page-base")