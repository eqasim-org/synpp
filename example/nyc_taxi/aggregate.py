import itertools

def configure(context):
    months = context.config("months")
    years = context.config("years")

    for year in years:
        for month in months:
            context.stage("nyc_taxi.download", { "month": month, "year": year })

def execute(context):
    months = context.config("months")
    years = context.config("years")

    return pd.concat([
        context.stage("nyc_taxi.download", { "month": month, "year": year })
        for month, year in itertools.product(months, years)
    ])
