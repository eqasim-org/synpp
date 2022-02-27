def configure(context):
    #context.stage("tests.fixtures.downstream.chain_a", { "a": context.config("a") }, alias = "dep")
    context.stage("tests.fixtures.downstream.chain_a", alias = "dep")

def execute(context):
    return context.stage("dep") * 10
