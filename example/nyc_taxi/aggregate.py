import itertools
import pandas as pd

"""
This stage retrieves a list of months and years from the configuration options
and constructs dependencies on nyc_taxi.download(month, year). So before this
stage can be executed, all data sets must be downloaded. Afterwards, we simply
load all the partial data sets an concatenate them to an overall pandas
data frame.
"""

def configure(context):
    # Get config options (lists)
    months = context.config("months")
    years = context.config("years")

    # Add dependencies to parametrized download stage
    for year in years:
        for month in months:
            context.stage("nyc_taxi.download", { "month": month, "year": year })

def execute(context):
    months = context.config("months")
    years = context.config("years")

    # Get the dependency stages and concatenate them
    return pd.concat([
        context.stage("nyc_taxi.download", { "month": month, "year": year })
        for month, year in itertools.product(months, years)
    ])
