def configure(context):
    context.config("a", volatile = True, default = 100)
    context.config("u.v.w", volatile = True, default = 0)
    context.config("xyz")

def execute(context):
    return context.config("a") + context.config("u.v.w") + context.config("xyz")
