def configure(context):
    context.config("a", 1)
    context.parameter("b", 20)

def runner(context, argument):
    return context.config("a") + context.parameter("b") + context.data("c") + argument

def execute(context):
    arguments = [1000, 2000, 3000, 4000, 5000]
    data = { "c": 300 }

    with context.parallel(data) as parallel:
        result = parallel.map(runner, arguments)

    return result
