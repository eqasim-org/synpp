def configure(context):
    context.stage("tests.fixtures.sum_config")
    context.stage("tests.fixtures.sum_params", { "a": 5, "b": 6 }, alias = "sum_params")

def execute(context):
    x = context.stage("tests.fixtures.sum_config")
    y = context.stage("sum_params")
    return x + y + 10
