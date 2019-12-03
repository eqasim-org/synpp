def configure(context):
    context.stage("tests.fixtures.sum_stages")

def execute(context):
    return context.stage("tests.fixtures.sum_stages")
