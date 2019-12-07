def configure(context):
    context.stage("tests.fixtures.devalidate_a")

def execute(context):
    return context.stage("tests.fixtures.devalidate_a")
