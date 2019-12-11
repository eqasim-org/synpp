from urllib.request import urlretrieve
import pandas as pd

def configure(context):
    context.parameter("year")
    context.parameter("month")
    context.config("base_url")

def execute(context):
    # The taxi data can be retrieved from, e.g.
    #    https://s3.amazonaws.com/nyc-tlc/trip+data/yellow_tripdata_2018-01.csv

    url = "%s/yellow_tripdata_%d-%02d.csv" % (
        context.config("base_url"),
        context.parameter("year"),
        context.parameter("month")
    )

    # We download the file from the URL to data.csv in the cache path
    with context.progress(label = "Downloading taxi data...") as progress:
        progress = DownloadProgress(progress)
        urlretrieve(url, "%s/data.csv" % context.path(), reporthook = progress)

    # And return a pandas data frame of the CSV as the result of the stage
    return pd.read_csv("%s/data.csv" % context.path())

class DownloadProgress:
    def __init__(self, progress):
        self.progress = progress
        self.initialized = False

    def __call__(self, count, block_size, total_size):
        if not self.initialized:
            self.progress.reset(total = total_size)

        self.initialized = True
        self.progress.update(block_size)
