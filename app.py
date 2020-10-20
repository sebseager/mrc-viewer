from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import dash_table as dt
import dash_daq as daq
import dash_auth as da
import dash_uploader as du
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import base64
from io import BytesIO, StringIO
import mrcfile
# from mrcfile import mrcinterpreter
import os
from pathlib import Path
import hashlib
import uuid
import util

external_stylesheets = ['/assets/style.css']
UPLOAD_ROOT = 'uploads'

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

du.configure_upload(app, UPLOAD_ROOT)

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
def get_app_layout():
    return html.Div([
        dcc.Store(id='boxfile-memory', data={'boxfile-counter': 0, 'boxfiles': {}, 'filenames': {}, 'filehashes': {}}),
        html.Div([
            html.Div([
                html.H3('Particle Coordinates'),
                du.Upload(
                    id='upload-box',
                    max_file_size=100,  # in MB
                    max_files=1,
                    upload_id=str(uuid.uuid1()),  # unique session id
                    text='Drag and Drop or Select File',
                    text_completed='Upload complete: ',
                    default_style={
                        'lineHeight': '80px',
                        'borderWidth': '1px',
                        'borderStyle': 'dashed',
                        'borderRadius': '10px',
                        'textAlign': 'center',
                        'marginLeft': '20px',
                        'width': 'calc(100% - 40px)'
                    },
                ),
                # dcc.Upload(
                #     id='upload-box',
                #     children=html.Div([
                #         'Drag and Drop'
                #     ]),
                #     style={
                #         'height': '60px',
                #         'lineHeight': '60px',
                #         'borderWidth': '1px',
                #         'borderStyle': 'dashed',
                #         'borderRadius': '5px',
                #         'textAlign': 'center',
                #         'marginLeft': '20px',
                #         'marginRight': '20px'
                #     },
                #     # Allow multiple files to be uploaded
                #     multiple=False
                # ),

                html.Div([
                    dcc.Checklist(
                        options=[
                            {'label': ' None available yet', 'disabled': True, 'value': 'none'},
                        ],
                        value=['none'],
                        id='boxfile-checklist'
                    ),
                    html.Br(),
                    html.H4('Options'),
                    html.Div([
                        html.Div([manual_boxsize_title], id='manual-boxsize-title'),
                        dcc.Input(
                            id='manual-boxsize',
                            placeholder='default: parse from file if possible',
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
                            'Show 75% of boxes (random)',
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
                        )
                    ]),
                    html.Br(),
                    html.Div([
                        html.H6(
                            'Show boxes missing confidence values',
                            style={
                                'marginLeft': '20px',
                                'marginRight': '20px'
                            }),
                        daq.BooleanSwitch(
                            id='no-conf-boxes-switch',
                            on=True
                        )
                    ], style={
                        'display': 'flex',
                        'alignItems': 'center'
                    }),
                    html.P(
                        'Applies to starred (*) coordinate files above.',
                        id='conf-applies-to',
                        style={
                            'fontStyle': 'italic',
                            'marginLeft': '20px',
                            'marginRight': '20px'
                        }),
                    html.Br(),
                    html.Div([
                        html.Button(
                            'Apply To Micrograph',
                            id='apply-btn',
                            style={
                                'marginBottom': '20px'
                            })
                    ], style={
                        'textAlign': 'right'
                    }),
                    html.H4('Display coordinate file'),
                    html.Div([
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
                html.H3('Electron Micrograph', id='mrc-name'),
                du.Upload(
                    id='upload-image',
                    max_file_size=1800,  # in MB
                    max_files=1,
                    filetypes=['mrc', 'mrcs'],
                    upload_id=str(uuid.uuid1()),  # unique session id
                    text='Drag and Drop or Select File',
                    text_completed='Upload complete: ',
                    default_style={
                        'lineHeight': '80px',
                        'borderWidth': '1px',
                        'borderStyle': 'dashed',
                        'borderRadius': '10px',
                        'textAlign': 'center',
                        'marginLeft': '20px',
                        'width': 'calc(100% - 40px)'
                    },
                ),
                # dcc.Upload(
                #     id='upload-image',
                #     children=html.Div(['Drag and Drop']),
                #     style={
                #         'height': '60px',
                #         'lineHeight': '60px',
                #         'borderWidth': '1px',
                #         'borderStyle': 'dashed',
                #         'borderRadius': '5px',
                #         'textAlign': 'center',
                #         'marginLeft': '20px',
                #         'marginRight': '20px'
                #     },
                #     # Allow multiple files to be uploaded
                #     multiple=False
                # ),
                html.Div([
                    dcc.Graph(
                        id="micrograph",
                        figure=go.Figure(
                            layout={
                                'shapes': [],
                                # 'paper_bgcolor': 'rgba(0,0,0,0)',
                                # 'plot_bgcolor': 'rgba(0,0,0,0)',
                                'autosize': True,
                                'margin': dict(l=0, r=0, b=0, t=35, pad=5),
                                'yaxis': {
                                    'scaleanchor': 'x',
                                    'scaleratio': 1
                                }
                            }
                        ),
                        style={
                            'width': 'calc(100vh - 250px)',
                            'height': 'calc(100vh - 250px)',
                            'marginTop': '15px',
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


app.layout = get_app_layout  # use the function so unique UUIDs are set


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
    return 'Show %s%% of boxes (random)' % value


@app.callback(
    Output('boxfile-table', 'columns'),
    Output('boxfile-table', 'data'),
    [Input('boxfile-dropdown', 'value')],
    [State('boxfile-memory', 'data')])
def display_boxfile_table(dropdown_value, data):
    tbl_cols = []
    tbl_data = []
    if dropdown_value is not None and str(dropdown_value) in data['boxfiles']:
        print("INFO: displaying table")
        df = pd.DataFrame(data['boxfiles'][str(dropdown_value)])
        tbl_cols = [{'name': i, 'id': i} for i in df.columns]
        tbl_data = df.to_dict('records')

    return tbl_cols, tbl_data


@app.callback(
    Output('output-image-upload', 'children'),
    Output('mrc-name', 'children'),
    [Input('upload-image', 'isCompleted')],
    [State('upload-image', 'fileNames')],
    [State('upload-image', 'upload_id')],
    [State('micrograph', 'figure')],
    [State('micrograph', 'style')],
    [State('micrograph', 'config')])
def load_micrograph(upload_done, filenames, upload_id, graph_figure, graph_style, graph_config):
    fig = go.Figure()
    filename = 'Electron Micrograph'
    if upload_done and filenames:
        filename = filenames[0]
        print("INFO: loading mrc")
        with mrcfile.open(Path(UPLOAD_ROOT) / upload_id / filename, mode='r', permissive=True) as mrc:
            # content_type, content_string = contents.split(',')
            # decoded = base64.b64decode(content_string)
            # interpreter = mrcinterpreter.MrcInterpreter(iostream=BytesIO(decoded), permissive=True)
            # mrc_raw = interpreter.data
            mrc_raw = mrc.data
            mrc_histeq = util.hist_equalize(mrc_raw)

            fig = px.imshow(mrc_histeq, binary_string=True, origin='lower', aspect='equal')

        if 'data' in graph_figure:
            for trace in graph_figure['data']:
                if trace not in fig['data'] and (trace['type'] == 'scatter' or trace['type'] == 'scattergl'):
                    fig.add_trace(trace)

        print("INFO: loading mrc done")

    fig.update_layout(graph_figure['layout'])

    return html.Div([
        dcc.Graph(
            id='micrograph',
            figure=fig,
            style=graph_style,
            config=graph_config
        )]), filename


@app.callback(
    Output('boxfile-checklist', 'options'),
    Output('boxfile-checklist', 'value'),
    Output('boxfile-dropdown', 'options'),
    [Input('boxfile-memory', 'data')],
    [State('boxfile-checklist', 'options')],
    [State('boxfile-checklist', 'value')])
def update_boxfile_checklist(data, checklist_opts, checklist_vals):
    loaded_boxfiles = data['filenames']
    print("INFO: checklist updated (loaded_boxfiles = %s)" % len(loaded_boxfiles))
    if len(loaded_boxfiles) == 0:
        return checklist_opts, checklist_vals, []
    else:
        boxfile_list = [{'label': ' %s (%s): %s' % (k, util.get_color(k)[1], v), 'disabled': True, 'value': k}
                        for k, v in loaded_boxfiles.items()]
        for i in range(len(boxfile_list)):
            if (pd.DataFrame(data['boxfiles'][str(i + 1)])['conf'] == util.NO_CONF_VAL).all():
                boxfile_list[i]['label'] = ' *' + boxfile_list[i]['label']
        all_vals = [k for k, _ in loaded_boxfiles.items()]
        dropdown_list = []
        for d in boxfile_list:
            e = d.copy()
            e.update({'disabled': False})
            dropdown_list.append(e)
        return boxfile_list, all_vals, dropdown_list


@app.callback(
    Output('boxfile-memory', 'data'),
    Output('manual-boxsize-title', 'children'),
    Output('micrograph', 'figure'),
    [Input('upload-box', 'isCompleted')],
    [Input('apply-btn', 'n_clicks')],
    [State('upload-box', 'fileNames')],
    [State('upload-box', 'upload_id')],
    [State('manual-boxsize', 'value')],
    [State('boxfile-memory', 'data')],
    [State('micrograph', 'figure')],
    [State('box-percent-slider', 'value')],
    [State('conf-range-slider', 'value')],
    [State('no-conf-boxes-switch', 'on')])
def store_box(upload_done, n_clicks, filenames, upload_id, manual_boxsize, data, figure, box_percent, conf_range,
              show_no_conf_boxes):
    fig = go.Figure(data=figure['data'], layout=figure['layout'])

    if upload_done and filenames:
        for filename in filenames:
            print("INFO: storing boxfile (filename = %s)" % filename)
            with open(Path(UPLOAD_ROOT) / upload_id / filename, mode='r') as file:
                file_str = file.read()
                # content_type, content_string = contents.split(',')
                # decoded = base64.b64decode(content_string)
                # last_uploaded_df = util.parse_boxfile(StringIO(boxfile.decode('utf-8')), filename, manual_boxsize)
                hashed = hashlib.md5(file_str.encode('utf-8')).hexdigest()
                last_uploaded_df = util.parse_boxfile(file_str, filename, manual_boxsize)

            fig['data'] = [trace for trace in fig['data'] if trace['type'] != 'scatter' and trace['type'] != 'scattergl']
            for i in range(1, data['boxfile-counter'] + 1):
                df = pd.DataFrame(data['boxfiles'][str(i)])
                boxes = util.filter_df(df, box_percent, conf_range, keep_no_conf=show_no_conf_boxes)
                fig.add_traces(util.make_trace(boxes, util.get_color(i)[0], data['filenames'][str(i)],
                                               data['filehashes'][str(i)]))

            if hashed in data['filehashes'].values():
                return data, manual_boxsize_title, fig

            if last_uploaded_df is None:
                return data, manual_boxsize_warning, fig

            data['boxfile-counter'] = data['boxfile-counter'] + 1
            data['filenames'][data['boxfile-counter']] = filename
            data['filehashes'][data['boxfile-counter']] = hashed
            data['boxfiles'][data['boxfile-counter']] = last_uploaded_df.to_dict()

            boxes = util.filter_df(last_uploaded_df, box_percent, conf_range, keep_no_conf=show_no_conf_boxes)

            fig.add_traces(util.make_trace(boxes, util.get_color(data['boxfile-counter'])[0], filename, hashed))

    fig.update_layout({
        'legend': {
            'orientation': 'h',
            'yanchor': 'top',
            'y': -0.07,
            'xanchor': 'center',
            'x': 0.5
        }
    })

    print("INFO: boxfile storage reloaded")
    # print(fig)
    return data, manual_boxsize_title, fig


try:
    get_ipython
    app.run_server(mode='inline')
    print("Detected IPython environment (running inline)")
except Exception:
    if __name__ == '__main__':
        app.run_server(debug=False)
        print("Running in server mode")
