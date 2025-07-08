def configure(context):
    context.stage("tests.fixtures.devalidation.volatile_a")

def execute(context):
    return context.stage("tests.fixtures.devalidation.volatile_a")
