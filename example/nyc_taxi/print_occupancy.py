"""
This stage takes the concatenated taxi data set and calculates the mean value
of passenger count in this data frame.
"""

def configure(context):
    context.stage("nyc_taxi.aggregate")

def execute(context):
    df = context.stage("nyc_taxi.aggregate")

    print("Average occupancy:", df["passenger_count"].mean())
