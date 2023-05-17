def configure(context):
    context.stage("tests.fixtures.devalidation.D", config={"d": 10}, alias="d")
    context.stage("tests.fixtures.devalidation.C")
    context.stage("tests.fixtures.devalidation.E1")
    context.stage("tests.fixtures.devalidation.E2")

def execute(context):
    context.stage("tests.fixtures.devalidation.E1")
    context.stage("tests.fixtures.devalidation.E2")
    context.stage("d")
    return context.stage("tests.fixtures.devalidation.C")
