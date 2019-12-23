def configure(context):
    context.stage("tests.fixtures.downstream.chain_c", { "a": 5 }, alias = "s1")
    context.stage("tests.fixtures.downstream.chain_c", { "a": 10 }, alias = "s2")

def execute(context):
    return context.stage("s1") + context.stage("s2")
