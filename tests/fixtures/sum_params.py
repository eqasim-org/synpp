def configure(context):
    context.parameter("a")
    context.parameter("b")

def execute(context):
    a, b = context.parameter("a"), context.parameter("b")
    return a + b
