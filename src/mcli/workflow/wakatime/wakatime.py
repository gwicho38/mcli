import click


@click.group(name="wakatime")
def wakatime():
    """WakaTime commands."""


if __name__ == "__main__":
    wakatime()
