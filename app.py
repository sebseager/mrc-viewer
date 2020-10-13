from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import dash_table as dt
import dash_auth as da
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import base64
from io import BytesIO, StringIO
from mrcfile import mrcinterpreter
import os
import util

external_stylesheets = ['/assets/style.css']

try:  # check if we're running in a notebook (not defined outside of IPython)
    get_ipython  # syntax warnings are fine here
    from jupyter_dash import JupyterDash
    app = JupyterDash(__name__, external_stylesheets=external_stylesheets)
except Exception:  # otherwise assume we're on a server
    from dash import Dash
    app = Dash(__name__, external_stylesheets=external_stylesheets)
    server = app.server  # for gunicorn deployment
    is_heroku = os.environ.get('IS_HEROKU', None)  # detect Heroku deployment
    if is_heroku:
        collab_user = os.environ.get('COLLAB_USER', None)  # basic HTTP auth
        collab_key = os.environ.get('COLLAB_SECRET', None)
        auth = da.BasicAuth(app, {collab_user: collab_key})


# cache = Cache(app.server, config={
#     'CACHE_TYPE': 'filesystem',
#     'CACHE_DIR': 'cache'
# })

# reusable layout elements
manual_boxsize_title = html.H6(
    'Manual box size',
    style={
        'marginLeft': '20px'
    })

manual_boxsize_warning = html.H6(
    'Manual box size required for this file',
    style={
        'marginLeft': '20px',
        'color': 'red'
    })

# main layout
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
                    html.Div([manual_boxsize_title], id='manual-boxsize-title'),
                    dcc.Input(
                        id='manual-boxsize',
                        placeholder='default: parse from file',
                        type='number',
                        min=0,
                        value='',
                        style={
                            'marginLeft': '20px',
                            'width': 'calc(100% - 20px)'
                        }
                    ),
                ]),
                html.Br(),
                html.Div([
                    html.H6(
                        'Show 75% of boxes',
                        id='box-percent-label',
                        style={
                            'marginLeft': '20px',
                            'marginRight': '20px'
                        }),
                    dcc.Slider(
                        id='box-percent-slider',
                        min=0,
                        max=100,
                        step=1,
                        value=75,
                        updatemode='drag'
                    )
                ]),
                html.Div([
                    html.H6(
                        'Confidence range (75-100%)',
                        id='conf-range-label',
                        style={
                            'marginLeft': '20px',
                            'marginRight': '20px'
                        }),
                    dcc.RangeSlider(
                        id='conf-range-slider',
                        min=0,
                        max=100,
                        step=1,
                        value=[75, 100],
                        marks={
                            0: {'label': '0%'},
                            60: {'label': '60%'},
                            75: {'label': '75%'},
                            90: {'label': '90%'},
                            100: {'label': '100%'}
                        },
                        pushable=5,
                        updatemode='drag'
                    ),
                    html.P(
                        'Applies to the following coordinate files: ',
                        id='conf-applies-to',
                        style={
                            'marginLeft': '20px',
                            'marginRight': '20px'
                        }),
                ]),
                html.Br(),
                html.Div([
                    html.Button(
                        'Apply All',
                        id='apply-btn',
                        style={
                            'marginBottom': '20px'
                        })
                ], style={
                    'textAlign': 'right'
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
                        id='boxfile-table',
                        sort_action='native',
                        filter_action='native'
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
                    figure=go.Figure(
                        layout={
                            'shapes': [],
                            'autosize': True,
                            'margin': dict(l=5, r=5, b=5, t=40, pad=2)
                        }
                    ),
                    style={
                        'width': 'calc(100vh - 200px)',
                        'height': 'calc(100vh - 200px)',
                        'display': 'inline-block'
                    },
                    config={
                        'responsive': True,
                        'displaylogo': False,
                        'watermark': False
                    }
                )], id='output-image-upload')
        ], className="seven columns"),
    ], className="row"),
], style={
    'textAlign': 'center'
})


@app.callback(
    Output('conf-range-label', 'children'),
    [Input('conf-range-slider', 'value')]
)
def box_slider_changed(value):
    return 'Confidence range (%s-%s%%)' % (value[0], value[1])


@app.callback(
    Output('box-percent-label', 'children'),
    [Input('box-percent-slider', 'value')]
)
def box_slider_changed(value):
    return 'Show %s%% of boxes' % value


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
        print("INFO: displaying table")
        df = pd.DataFrame(data[selected_boxfile])
        tbl_cols = [{'name': i, 'id': i} for i in df.columns]
        tbl_data = df.to_dict('records')

    return tbl_cols, tbl_data


@app.callback(
    Output('output-image-upload', 'children'),
    Output('mrc-name', 'children'),
    Output('upload-box', 'disabled'),
    [Input('upload-image', 'contents')],
    [State('upload-image', 'filename')],
    [State('micrograph', 'figure')],
    [State('micrograph', 'style')],
    [State('micrograph', 'config')])
def load_micrograph(contents, filename, graph_figure, graph_style, graph_config):
    fig = go.Figure()
    filename = filename or 'Micrograph'
    box_upload_disabled = False  # we don't need to keep boxfile upload disabled until a micrograph is loaded anymore
    if contents is not None:
        print("INFO: loading mrc")
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        interpreter = mrcinterpreter.MrcInterpreter(iostream=BytesIO(decoded), permissive=True)
        mrc_raw = interpreter.data
        mrc_histeq = util.hist_equalize(mrc_raw)

        fig = px.imshow(mrc_histeq, binary_string=True, origin='lower', aspect='equal')

        box_upload_disabled = False
        print("INFO: loading mrc done")
    else:
        print("INFO: micrograph relayout")

    fig.update_layout(graph_figure['layout'])

    return html.Div([
        dcc.Graph(
            id='micrograph',
            figure=fig,
            style=graph_style,
            config=graph_config
        )]), filename, box_upload_disabled


@app.callback(
    Output('boxfile-memory', 'data'),
    Output('manual-boxsize-title', 'children'),
    [Input('upload-box', 'contents')],
    [Input('apply-btn', 'n_clicks')],
    [State('manual-boxsize', 'value')],
    [State('upload-box', 'filename')],
    [State('boxfile-memory', 'data')])
def store_box(contents, n_clicks, manual_boxsize, filename, data):
    data = data or {'boxfile-counter': 0, 'filenames': {}}

    if contents is not None and filename not in data['filenames'].values():
        print("INFO: storing boxfile (filename = %s)" % filename)
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = util.parse_boxfile(StringIO(decoded.decode('utf-8')), filename, manual_boxsize)
        if df is None:
            return data, manual_boxsize_warning
        # rects = [
        #     util.make_rect(row['x'], row['y'], row['w'], row['h'], util.get_color(data['boxfile-counter'])[0] + 1)
        #     for i, row in df.iterrows() if len(row) > 1
        # ]
        data['boxfile-counter'] = data['boxfile-counter'] + 1
        data['filenames'][data['boxfile-counter']] = filename
        data['boxfile_%s' % data['boxfile-counter']] = df.to_dict()
        # data['rects_%s' % data['boxfile-counter']] = rects

    print("INFO: boxfile storage reloaded")
    return data, manual_boxsize_title


@app.callback(
    Output('boxfile-checklist', 'options'),
    Output('boxfile-dropdown', 'options'),
    [Input('boxfile-memory', 'data')])
def update_boxfile_checklist(data):
    data = data or {'boxfile-counter': 0, 'filenames': {}}
    loaded_boxfiles = data['filenames']
    print("INFO: checklist updated (loaded_boxfiles = %s)" % len(loaded_boxfiles))
    if len(loaded_boxfiles) == 0:
        return [{'label': 'None available yet', 'disabled': True, 'value': 'none'}], []
    else:
        boxfile_list = [{'label': ' %s (%s): %s' % (k, util.get_color(k)[1], v), 'disabled': False, 'value': k}
                        for k, v in loaded_boxfiles.items()]
        return boxfile_list, boxfile_list


@app.callback(
    Output('micrograph', 'figure'),
    [Input('boxfile-memory', 'data')],
    [Input('apply-btn', 'n_clicks')],
    [Input('boxfile-checklist', 'value')],
    [State('micrograph', 'figure')],
    [State('box-percent-slider', 'value')],
    [State('conf-range-slider', 'value')])
def update_graph(data, n_clicks, checklist_vals, figure, box_percent, conf_range):
    fig = go.Figure(data=figure['data'], layout=figure['layout'])
    all_rects = []
    all_traces = []
    if data is not None and data['boxfile-counter'] > 0:
        print("INFO: updating graph overlay (counter = %s)" % data['boxfile-counter'])
        for i in range(1, data['boxfile-counter'] + 1):
            visible = str(i) in checklist_vals
            boxes = pd.DataFrame(data['boxfile_%s' % i])
            boxes = boxes.loc[(boxes['conf'] >= conf_range[0] / 100) & (boxes['conf'] <= conf_range[1] / 100)]
            boxes = boxes.sample(frac=box_percent / 100)
            rects = [
                util.make_rect(row['x'], row['y'], row['w'], row['h'], util.get_color(data['boxfile-counter'])[0],
                               vis=visible) for i, row in boxes.iterrows() if len(row) > 1
            ]
            all_rects.extend(rects)

    updated_layout = figure['layout']
    updated_layout['shapes'] = all_rects if len(all_rects) > 0 else [util.make_rect(0, 0, 1, 1, 'orange', vis=True)]
    fig.update_layout(updated_layout)

    print("INFO: graph reloaded")
    return fig


try:
    get_ipython
    app.run_server(mode='inline')
    print("Detected IPython environment (running inline)")
except Exception:
    if __name__ == '__main__':
        app.run_server(debug=True)  # TODO: set to False before deploying
        print("Running in server mode")
