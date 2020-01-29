def configure(context):
    context.stage("tests.fixtures.ephemeral.A")
    context.ephemeral = True

def execute(context):
    pass
