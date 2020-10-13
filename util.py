from matplotlib import pyplot as plt
import numpy as np
import os
import pandas as pd

BOX_COLORS = ['#ff7f00', '#4daf4a', '#f781bf', '#a65628', '#984ea3', '#e41a1c', '#dede00', '#377eb8', '#999999']
BOX_COLOR_NAMES = ['orange', 'green', 'pink', 'brown', 'violet', 'crimson', 'lime', 'steel blue', 'light gray']


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


# make rect and scatter trace for dcc.Graph figure given box data (assume x, y are at center of box)
def make_rect(x, y, w, h, c, vis=True):
    return dict(type='rect', line=dict(color=c, width=1.5), xsizemode='scaled', ysizemode='scaled',
                xref='x', yref='y', x0=x-w/2, y0=y-h/2, x1=x+w/2, y1=y+h/2, visible=vis)

def make_trace(df):
    return dict(type='rect', line=dict(color=c, width=1.5), xsizemode='scaled', ysizemode='scaled',
                xref='x', yref='y', x0=x - w / 2, y0=y - h / 2, x1=x + w / 2, y1=y + h / 2, visible=vis)


# read boxfile given filename, adjusting x, y to center of box if needed
def parse_boxfile(decoded_contents, filename, manual_boxsize):
    ext = os.path.splitext(filename)[-1].lower()
    df = pd.read_csv(decoded_contents, delim_whitespace=True, skipinitialspace=True, skip_blank_lines=True, header=None)
    print("MANUAL BOXSIZE")
    print(manual_boxsize)
    if ext in ['.box']:
        df = df.rename(columns={0: 'x', 1: 'y', 2: 'w', 3: 'h'})
        df['x'] = df['x'] + (df['w'] / 2)
        df['y'] = df['y'] + (df['y'] / 2)
        df['conf'] = [1.0] * len(df.index)
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
        df['conf'] = [1.0] * len(df.index)

    return df

