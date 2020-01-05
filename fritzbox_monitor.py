import collections
import json
import os
import time
import pandas as pd
import tables
from fritzconnection import FritzConnection
from fritzconnection.lib.fritzstatus import FritzStatus


class DataEntry(tables.IsDescription):
    timestamp = tables.UInt32Col()
    connected = tables.BoolCol()
    linked = tables.BoolCol()
    transmission_rate_up = tables.UInt16Col()
    transmission_rate_down = tables.UInt16Col()
    max_bitrate_up = tables.UInt16Col()
    max_bitrate_down = tables.UInt16Col()
    max_linked_bitrate_up = tables.UInt16Col()
    max_linked_bitrate_down = tables.UInt16Col()


class FritzBoxMonitor(object):
    def __init__(self, archive_dirpath: str, password: str = None):
        self.last_log_items = collections.deque(maxlen=100)
        self.password = password
        if not os.path.exists(archive_dirpath):
            os.makedirs(archive_dirpath)
        self.log_filepath = os.path.join(archive_dirpath, "logs.txt")
        self.data_filepath = os.path.join(archive_dirpath, "data.h5")
        if not os.path.exists(self.data_filepath):
            with tables.open_file(self.data_filepath, "w") as data_file:
                group = data_file.create_group("/", "data")
                data_file.create_table(group, "connection_data", DataEntry)

    def update_logs(self):
        print("Updating logs...")
        fc = FritzConnection(password=self.password)
        logs = fc.call_action('DeviceInfo:1', 'GetDeviceLog')
        new_log_items = logs["NewDeviceLog"].split("\n")
        n = min(len(new_log_items), self.last_log_items.maxlen)
        new_log_items = reversed(new_log_items[:n]) # Newest n, most recent at last position
        with open(self.log_filepath, "a") as log_file:
            for new_log_item in new_log_items:
                if new_log_item not in self.last_log_items:
                    self.last_log_items.append(new_log_item)
                    log_file.write(new_log_item + "\n")

    def update_data(self):
        print("Updating data...")
        fc = FritzConnection(password=self.password)
        fs = FritzStatus(fc)
        with tables.open_file(self.data_filepath, "a") as data_file:
            table = data_file.root.data.connection_data
            row = table.row
            row["timestamp"] = time.time()
            row["connected"] = fs.is_connected
            row["linked"] = fs.is_linked
            row["transmission_rate_up"] = fs.transmission_rate[0] * 8 / 1000
            row["transmission_rate_down"] = fs.transmission_rate[1] * 8 / 1000
            row["max_bitrate_up"] = fs.max_bit_rate[0] / 1000
            row["max_bitrate_down"] = fs.max_bit_rate[1] / 1000
            row["max_linked_bitrate_up"] = fs.max_linked_bit_rate[0] / 1000
            row["max_linked_bitrate_down"] = fs.max_linked_bit_rate[1] / 1000
            row.append()
            table.flush()

    def get_data(self) -> pd.DataFrame:
        print("Reading data from {}".format(self.data_filepath))
        with tables.open_file(self.data_filepath) as data_file:
            table = data_file.root.data.connection_data
            df = pd.DataFrame.from_records(table.read())
            return df


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(script_dir, "config.json")) as config_file:
        password = json.load(config_file)["password"]
    monitor = FritzBoxMonitor(os.path.join(script_dir, "output"), password)
    start = time.time()
    while time.time() - start < 864000:  # 10 days
        monitor.update_logs()
        monitor.update_data()
        time.sleep(1)


if __name__ == '__main__':
    main()
