def configure(context):
    context.config("a")

def execute(context):
    return context.config("a")
