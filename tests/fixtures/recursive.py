def configure(context):
    a = context.parameter("a")

    if a > 0:
        context.stage("tests.fixtures.recursive", { "a": a - 1 }, alias = "ralias")

def execute(context):
    if context.parameter("a") > 0:
        return context.stage("ralias") + context.parameter("a")

    return 0
