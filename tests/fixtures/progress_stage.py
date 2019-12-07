def execute(context):
    with context.progress(total = 1000, label = "ABC") as progress:
        for i in range(1000):
            progress.update()

    with context.progress(label = "ABC") as progress:
        for i in range(1000):
            progress.update()

    with context.progress() as progress:
        for i in range(1000):
            progress.update()
