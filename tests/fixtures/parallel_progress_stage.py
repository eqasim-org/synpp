import time

def runner(context, index):
    for i in range(10):
        context.progress.update()

def execute(context):
    with context.progress(total = 100) as progress:
        with context.parallel({}, processes = 4) as parallel:
            parallel.map(runner, list(range(10)))
            
