def configure(context):
    # context.stage("tests.fixtures.downstream.chain_b", { "a": context.config("a") }, alias = "dep")
    context.stage("tests.fixtures.downstream.chain_b", alias = "dep")

def execute(context):
    return context.stage("dep")
