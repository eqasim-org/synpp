def execute(context):
    with open("%s/output.txt" % context.path(), "w+") as f:
        f.write("abc_uvw")
