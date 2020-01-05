import argparse
from datetime import datetime
from itertools import groupby
import matplotlib.pyplot as plt
from fritzbox_monitor import FritzBoxMonitor

from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()

def parse_outages(data):
    outages = []
    interval_start = -1
    interval_end = -1
    for idx, up in enumerate(data["connected"]):
        if not up:
            interval_end = idx
        else:
            if interval_start < interval_end:
                outages.append((interval_start, interval_end))
            interval_start = idx + 1
    return outages


def main(args):
    data = FritzBoxMonitor(args.input_dir).get_data()
    times = list(map(lambda ts: datetime.fromtimestamp(ts), data["timestamp"].tolist()))
    outages = parse_outages(data)

    fig, axes = plt.subplots(len(data.columns) - 1, sharex="col", figsize=(20,18))
    data_columns = data.loc[:, data.columns != 'timestamp'].columns
    for i, column_name in enumerate(data_columns):
        axes[i].plot(times, data[column_name])
        axes[i].text(0.01, 0.8, column_name, transform=axes[i].transAxes, bbox={'facecolor': 'gray', 'alpha': 0.3})
        axes[i].grid(True)
        for outage in outages:
            axes[i].axvspan(times[outage[0]], times[outage[1]], alpha=0.3, color='red')
    fig.autofmt_xdate()
    fig.subplots_adjust(left=0.05, bottom=0.06, right=0.99, top=0.96)
    plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir", type=str)
    main(parser.parse_args())