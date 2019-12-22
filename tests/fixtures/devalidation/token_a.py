def configure(context):
    context.config("path")

def read(path):
    with open(path) as f:
        return f.read()

def execute(context):
    return read(context.config("path"))

def validate(context):
    return read(context.config("path"))
