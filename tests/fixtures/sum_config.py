def configure(context):
    context.config("a")
    context.config("b")

def execute(context):
    a, b = context.config("a"), context.config("b")
    return a + b
