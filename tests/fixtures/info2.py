def configure(context):
    context.stage("tests.fixtures.info1")

def execute(context):
    context.info("abc", "123")
