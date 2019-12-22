def configure(context):
    a = context.config("a")

    if a > 0:
        context.stage("tests.fixtures.recursive", { "a": a - 1 }, alias = "ralias")

def execute(context):
    if context.config("a") > 0:
        return context.stage("ralias") + context.config("a")

    return 0
