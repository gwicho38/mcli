import click


@click.group(name="workflow")
def workflow():
    """Workflow commands"""
    pass


if __name__ == "__main__":
    workflow()
