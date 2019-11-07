def configure(context):
    context.param("a")
    context.param("b")

def execute(context):
    a, b = context.param("a"), context.param("b")
    return a + b
