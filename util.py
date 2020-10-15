from matplotlib import pyplot as plt
import numpy as np
import os
import pandas as pd
import plotly.graph_objects as go

BOX_COLORS = ['#ff7f00', '#4daf4a', '#f781bf', '#a65628', '#984ea3', '#e41a1c', '#dede00', '#377eb8']
BOX_COLOR_NAMES = ['orange', 'green', 'pink', 'brown', 'violet', 'crimson', 'lime', 'steel blue']
NO_CONF_VAL = -1.0


def get_color(i):
    idx = int(i) % len(BOX_COLORS)
    return BOX_COLORS[idx], BOX_COLOR_NAMES[idx]


# perform histogram equalization on 2D image array
def hist_equalize(img_arr):
    hist_fig = plt.figure()
    hist_arr, bins, _ = plt.hist(img_arr.ravel(), bins='auto', density=True)
    cdf = hist_arr.cumsum()  # cumulative distribution function
    cdf = 255 * cdf / cdf[-1]  # normalize
    plt.close(hist_fig)
    img_equalized = np.interp(img_arr.ravel(), bins[:-1], cdf)
    return np.array(img_equalized.reshape(img_arr.shape))


# make rect for dcc.Graph figure given box data (assume x, y are at center of box)
def make_rect(x, y, w, h, c, vis=True):
    return dict(type='rect', line=dict(color=c, width=1.5), xsizemode='scaled', ysizemode='scaled',
                xref='x', yref='y', x0=x-w/2, y0=y-h/2, x1=x+w/2, y1=y+h/2, visible=vis)


# make scatter trace for given df (boxfile)
def make_trace(df, color, filename, filehash):
    x = []
    y = []
    data = []
    for i, row in df.iterrows():
        x0 = row['x'] - row['w'] / 2
        x1 = row['x'] + row['w'] / 2
        y0 = row['y'] - row['h'] / 2
        y1 = row['y'] + row['h'] / 2
        x.extend([x0, x1, x1, x0, x0, None])  # have to bring the trace around to original point
        y.extend([y0, y0, y1, y1, y0, None])  # None terminates each box
        data.append((row['x'], row['y'], row['conf']))

    if len(x) == 0 or len(y) == 0:
        return []

    if x[-1] is None:
        del x[-1]
    if y[-1] is None:
        del y[-1]

    return [go.Scattergl(x=x, y=y, mode='lines', line={'color': color}, name=filename, legendgroup=filehash,
                         showlegend=True, hoverinfo='none'),
            go.Scattergl(x=list(zip(*data))[0], y=list(zip(*data))[1], mode='markers', marker={'color': color},
                         opacity=0, name=filename, legendgroup=filehash, showlegend=False, customdata=data,
                         hovertemplate='<b>confidence</b>: %{customdata[2]:.2f}' +
                                       '<br>center-x: %{customdata[0]:.2f}' +
                                       '<br>center-y: %{customdata[1]:.2f}')]


def filter_df(df, box_percent, conf_range, keep_no_conf=True):
    conf_low = conf_range[0] / 100
    conf_high = conf_range[1] / 100
    if keep_no_conf:
        boxes = df.loc[((df['conf'] >= conf_low) & (df['conf'] <= conf_high)) | (df['conf'] == -1)]
    else:
        boxes = df.loc[(df['conf'] >= conf_low) & (df['conf'] <= conf_high)]
    boxes = boxes.sample(frac=box_percent / 100)
    print("BOXES")
    print(boxes)
    return boxes


# read boxfile given filename, adjusting x, y to center of box if needed
def parse_boxfile(decoded_contents, filename, manual_boxsize):
    ext = os.path.splitext(filename)[-1].lower()
    print(decoded_contents)
    df = pd.read_csv(decoded_contents, delim_whitespace=True, skipinitialspace=True, skip_blank_lines=True, header=None)
    print("INFO: using manual boxsize %s for file %s" % (manual_boxsize, filename))
    if ext in ['.box']:
        df = df.rename(columns={0: 'x', 1: 'y', 2: 'w', 3: 'h'})
        df['x'] = df['x'] + (df['w'] / 2)
        df['y'] = df['y'] + (df['h'] / 2)
        df['conf'] = [NO_CONF_VAL] * len(df.index)
    elif ext in ['.cbox']:
        df = df.rename(columns={0: 'x', 1: 'y', 2: 'w', 3: 'h', 4: 'conf'})
        df['x'] = df['x'] + (df['w'] / 2)
        df['y'] = df['y'] + (df['h'] / 2)
    elif ext in ['.star']:
        if manual_boxsize is None or manual_boxsize == "":
            return None
        pass
    elif ext in ['.coord']:
        if manual_boxsize is None or manual_boxsize == "":
            return None
        df = df.rename(columns={0: 'x', 1: 'y'})
        df['w'] = df['h'] = [manual_boxsize] * len(df.index)
        df['conf'] = [NO_CONF_VAL] * len(df.index)

    return df

