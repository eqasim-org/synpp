def configure(context):
    context.stage("nyc_taxi.aggregate")

def execute(context):
    print(context.stage("nyc_taxi.aggregate"))
