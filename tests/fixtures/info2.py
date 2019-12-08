def configure(context):
    context.stage("tests.fixtures.info1")

def execute(context):
    context.set_info("abc", "123")
    context.set_info("concat", "123" + context.get_info("tests.fixtures.info1", "uvw"))
