def configure(context):
    context.stage("tests.fixtures.cache_path_write")

def execute(context):
    with open("%s/output.txt" % context.path("tests.fixtures.cache_path_write")) as f:
        return f.read()
