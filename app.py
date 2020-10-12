import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import dash_table as dt
import dash_auth as da
import plotly.express as px
import plotly.graph_objects as go
from flask_caching import Cache
import pandas as pd
import base64
from io import BytesIO, StringIO
from mrcfile import mrcinterpreter
import os
import util

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']  # TODO: write local CSS

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
cache = Cache(app.server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'cache'
})

# basic HTTP auth
is_heroku = os.environ.get('IS_HEROKU', None)
if is_heroku:
    collab_user = os.environ.get('COLLAB_USER', None)
    collab_key = os.environ.get('COLLAB_KEY', None)
    auth = da.BasicAuth(
        app, {collab_user: collab_key}
    )


app.layout = html.Div([
    # dcc.Store(id='mrc-memory', data={'mrc': []}),
    dcc.Store(id='boxfile-memory', data={'boxfile-counter': 0, 'filenames': {}}),
    html.Div([
        html.Div([
            html.H3('Coordinates'),
            dcc.Upload(
                id='upload-box',
                children=html.Div([
                    'Drag and Drop'
                ]),
                style={
                    'height': '60px',
                    'lineHeight': '60px',
                    'borderWidth': '1px',
                    'borderStyle': 'dashed',
                    'borderRadius': '5px',
                    'textAlign': 'center',
                    'marginLeft': '20px',
                    'marginRight': '20px'
                },
                # Allow multiple files to be uploaded
                multiple=False
            ),

            html.Div([
                html.H4('Options'),
                html.Div([
                    html.H6(
                        'Manual box size',
                        style={
                            'marginLeft': '20px',
                            'marginRight': '20px'
                        }),
                    dcc.Input(
                        id='manual-boxsize',
                        placeholder='automatic',
                        type='number',
                        min=0,
                        value=''
                    ),
                    html.H6(
                        'required for this file',
                        id='box-size-required',
                        style={
                            'color': 'red',
                            'marginLeft': '20px',
                            'display': 'none'
                        })
                ], style={
                    'display': 'flex',
                    'alignItems': 'center'
                }),
                html.Br(),
                html.Button(
                    'Recalculate Boxes',
                    id='recalc-boxes',
                    style={
                        'marginLeft': '20px',
                        'marginBottom': '20px'
                    }),

                html.H4('Loaded coordinate files'),
                html.Div([
                    dcc.Checklist(
                        options=[
                            {'label': 'None available yet', 'disabled': True, 'value': 'none'},
                        ],
                        value=[],
                        id='boxfile-checklist'
                    ),
                    html.Br(),
                    dcc.Dropdown(
                        id='boxfile-dropdown',
                        placeholder='Select coordinate file to preview...'
                    ),
                    dt.DataTable(
                        id='boxfile-table'
                    )
                ], style={
                    'marginLeft': '20px'
                })
            ], style={
                'textAlign': 'left',
                'marginTop': '20px',
                'marginLeft': '20px',
                'marginRight': '20px'
            }, id='box-options'),
        ], className="five columns"),

        html.Div([
            html.H3('Micrograph', id='mrc-name'),
            dcc.Upload(
                id='upload-image',
                children=html.Div(['Drag and Drop']),
                style={
                    'height': '60px',
                    'lineHeight': '60px',
                    'borderWidth': '1px',
                    'borderStyle': 'dashed',
                    'borderRadius': '5px',
                    'textAlign': 'center',
                    'marginLeft': '20px',
                    'marginRight': '20px'
                },
                # Allow multiple files to be uploaded
                multiple=False
            ),
            html.Div([
                dcc.Graph(
                    id="micrograph",
                    animate=False,
                    figure=go.Figure(layout={
                        'shapes': []
                    }),
                    style={"width": "calc(100vh - 200px)", 'height': 'calc(100vh - 200px)', "display": "inline-block"}
                )], id='output-image-upload')
        ], className="seven columns"),
    ], className="row"),
], style={
    'textAlign': 'center'
})


@app.callback(
    Output('boxfile-table', 'columns'),
    Output('boxfile-table', 'data'),
    [Input('boxfile-dropdown', 'value')],
    [State('boxfile-memory', 'data')])
def display_boxfile_table(dropdown_value, data):
    selected_boxfile = 'boxfile_%s' % dropdown_value
    tbl_cols = []
    tbl_data = []
    if dropdown_value is not None and selected_boxfile in data:
        df = pd.DataFrame(data[selected_boxfile])
        print(df)
        tbl_cols = [{'name': i, 'id': i} for i in df.columns]
        tbl_data = df.to_dict('records')

    return tbl_cols, tbl_data


@app.callback(
    Output('output-image-upload', 'children'),
    Output('mrc-name', 'children'),
    Output('upload-box', 'disabled'),
    [Input('upload-image', 'contents')],
    [State('upload-image', 'filename')])
def load_micrograph(contents, filename):
    print("LOAD MRC")
    fig = go.Figure(layout={
        'autosize': True,
        'margin': dict(l=5, r=5, b=5, t=40, pad=2)
    })
    filename = filename or 'Micrograph'
    box_upload_disabled = False  # we don't need to keep boxfile upload disabled until a micrograph is loaded anymore
    if contents is not None:
        print("LOADING MRC")
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        interpreter = mrcinterpreter.MrcInterpreter(iostream=BytesIO(decoded), permissive=True)
        mrc_raw = interpreter.data
        mrc_histeq = util.hist_equalize(mrc_raw)

        fig = px.imshow(mrc_histeq, binary_string=True, origin='lower', aspect='equal')
        fig.update_layout(
            autosize=True,
            margin=dict(l=5, r=5, b=5, t=40, pad=2)
        )

        box_upload_disabled = False

    return html.Div([
        dcc.Graph(
            id="micrograph",
            figure=fig,
            style={"width": "calc(100vh - 200px)", 'height': 'calc(100vh - 200px)', "display": "inline-block"})
    ]), filename, box_upload_disabled


@app.callback(
    Output('boxfile-memory', 'data'),
    Output('box-size-required', 'style'),
    [Input('upload-box', 'contents')],
    [Input('manual-boxsize', 'value')],
    [State('upload-box', 'filename')],
    [State('boxfile-memory', 'data')],
    [State('box-size-required', 'style')])
def store_box(contents, manual_boxsize, filename, data, box_size_required):
    print("STORE BOX")
    data = data or {'boxfile-counter': 0, 'filenames': {}}
    if contents is not None and filename not in data['filenames'].values():
        print("STORING BOX")
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = util.parse_boxfile(StringIO(decoded.decode('utf-8')), filename, manual_boxsize)
        if df is None:
            box_size_required['display'] = 'inline'
            return data, box_size_required
        rects = [
            util.make_rect(
                row['x'], row['y'], row['w'], row['h'],
                util.BOX_COLORS[data['boxfile-counter'] % len(util.BOX_COLORS)])
            for i, row in df.iterrows() if len(row) > 1
        ]
        print(df)
        data['boxfile-counter'] = data['boxfile-counter'] + 1
        data['filenames'][data['boxfile-counter']] = filename
        data['boxfile_%s' % data['boxfile-counter']] = df.to_dict()
        data['rects_%s' % data['boxfile-counter']] = rects

    box_size_required['display'] = 'none'
    return data, box_size_required


@app.callback(
    Output('boxfile-checklist', 'options'),
    Output('boxfile-dropdown', 'options'),
    [Input('boxfile-memory', 'data')])
def update_boxfile_checklist(data):
    print("UPDATING CHECKLIST")
    data = data or {'boxfile-counter': 0, 'filenames': {}}
    loaded_boxfiles = data['filenames']
    print(loaded_boxfiles)
    if len(loaded_boxfiles) == 0:
        return [{'label': 'None available yet', 'disabled': True, 'value': 'none'}], []
    else:
        boxfile_list = [{'label': v, 'disabled': False, 'value': k} for k, v in loaded_boxfiles.items()]
        return boxfile_list, boxfile_list


@app.callback(
    Output('micrograph', 'figure'),
    [Input('boxfile-memory', 'data')],
    [Input('recalc-boxes', 'n_clicks')],
    [Input('boxfile-checklist', 'value')],
    [State('micrograph', 'figure')])
@cache.memoize(timeout=300)
def update_graph(boxfile_data, recalc_boxes_clicks, checklist_vals, figure):
    print("UPDATE BOXFILES")
    fig = go.Figure(data=figure['data'], layout=figure['layout'])
    shapes = []
    if boxfile_data is not None and boxfile_data['boxfile-counter'] > 0:
        for i in range(1, boxfile_data['boxfile-counter'] + 1):
            print("UPDATING BOXFILES")
            rects = boxfile_data['rects_%s' % i]
            if str(i) in checklist_vals:

                # for shape in boxfile_data['rects_%s' % i]:
                #     print(d_shape(shape)
                #     fig.adshape)
                # figure['layout']['shapes'] = boxfile_data['rects_%s' % i]
                # updated_layout.update({'shapes': })
                for d in rects:
                    d.update({'visible': True})
            else:
                for d in rects:
                    d.update({'visible': False})
            shapes.extend(rects)

    updated_layout = figure['layout']
    updated_layout['shapes'] = shapes
    fig.update_layout(updated_layout)
    print("DONE\n")

    return fig


if __name__ == '__main__':
    app.run_server(debug=False)
