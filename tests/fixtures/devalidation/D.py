def configure(context):
    d = context.config("d")
    context.stage("tests.fixtures.devalidation.A1", { "a": d }, alias = "a1")

def execute(context):
    return context.stage("a1")
