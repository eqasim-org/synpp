def configure(context):
    context.stage("tests.fixtures.devalidation.A1")
    context.stage("tests.fixtures.devalidation.A2")

def execute(context):
    a1 = context.stage("tests.fixtures.devalidation.A1")
    a2 = context.stage("tests.fixtures.devalidation.A2")

    return a1 + a2
