import warnings

import click
import requests

# Suppress the warning about python-Levenshtein
warnings.filterwarnings("ignore", message="Using slow pure-python SequenceMatcher")
from fuzzywuzzy import process

"""_summary_
    ssh -o GatewayPorts=yes -o ServerAliveInterval=60 -o ProxyCommand="ssh -W %h:%p myuser@my-proxy-server" -L80::80 -L443::443 myuser@localhost
Returns:
    _type_: _description_
    """


class DockerClient:
    def __init__(self, registry_url):
        self.registry_url = registry_url

    def _make_request(self, endpoint):
        url = f"{self.registry_url}/{endpoint}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.info(f"Error fetching data from {url}: {e}")
            return None

    def get_catalog(self):
        return self._make_request("v2/_catalog")

    def get_tags(self, repository):
        return self._make_request(f"v2/{repository}/tags/list")

    def search_repository(self, repository):
        catalog = self.get_catalog()
        if catalog:
            return [repo for repo in catalog.get("repositories", []) if repository in repo]
        return []

    def search_all_repositories(self, token: str):
        logger.info("search_all_repositories")
        catalog = self.get_catalog()
        response = []
        for repo in catalog.get("repositories", []):
            try:
                tags = self.get_tags(repository=repo).get("tags", [])
                query_results = process.extract(token, tags, limit=2)
                matching_tuples = [
                    (version, score) for version, score in query_results if score > 88
                ]
                if len(matching_tuples) > 0:
                    response.append(f"{repo}: {matching_tuples}")
                    logger.info(f"{repo}: {matching_tuples}")
            except Exception as e:
                logger.info(e)
                pass
        return response

    def count_images(self, repository):
        tags = self.get_tags(repository)
        if tags:
            return len(tags.get("tags", []))
        return 0


@click.group()
@click.option(
    "--registry-url",
    default="",
    help="URL of the Docker registry",
)
@click.pass_context
def registry(ctx, registry_url):
    """registry utility - use this to interact with the mcli Docker registry."""
    ctx.obj = DockerClient(registry_url)


@registry.command()
@click.pass_context
def catalog(ctx):
    """Fetch the catalog of repositories."""
    client = ctx.obj
    catalog = client.get_catalog()
    if catalog:
        click.echo("Catalog:")
        for repo in catalog.get("repositories", []):
            click.echo(f"  - {repo}")


@registry.command()
@click.argument("repository")
@click.option("--tag-name")
@click.pass_context
def tags(ctx, repository, tag_name):
    """Fetch the tags for a given repository."""
    client = ctx.obj
    tags = client.get_tags(repository)
    if tag_name:
        logger.info(tag_name)
    else:
        click.echo(f"Tags for repository '{repository}':")
        for tag in tags.get("tags", []):
            click.echo(f"  - {tag}")


@registry.command(name="search-tags")
@click.argument("repository")
@click.option("--tag-name")
@click.pass_context
def search_tags(ctx, repository, tag_name):
    """Fetch the tags for a given repository."""
    client = ctx.obj
    tags = client.get_tags(repository)
    if tag_name:
        logger.info(tag_name)
    else:
        click.echo(f"Tags for repository '{repository}':")
        for tag in tags.get("tags", []):
            click.echo(f"  - {tag}")


@registry.command()
@click.argument("repository")
@click.pass_context
def search(ctx, repository):
    """Search for a repository by name."""
    client = ctx.obj
    results = client.search_repository(repository)
    if results:
        click.echo(f"Search results for '{repository}':")
        for repo in results:
            click.echo(f"  - {repo}")


@registry.command()
@click.argument("repository")
@click.argument("tag")
@click.pass_context
def image_info(ctx, repository, tag):
    """Get detailed information about a specific image."""
    client = ctx.obj
    info = client.get_image_info(repository, tag)
    if info:
        click.echo(f"Image info for {repository}:{tag}:")
        click.echo(info)


@registry.command()
@click.argument("repository")
@click.pass_context
def count(ctx, repository):
    """Count the number of tags/images in a repository."""
    client = ctx.obj
    count = client.count_images(repository)
    click.echo(f"Number of tags in repository '{repository}': {count}")


@registry.command()
@click.argument("repository")
@click.argument("tag")
@click.pass_context
def pull(ctx, repository, tag):
    """Pull an image from the registry."""
    client = ctx.obj
    image = client.pull_image(repository, tag)
    if image:
        click.echo(f"Pulled image {repository}:{tag}")


# TODO: Implement the pull_image method in DockerClient


@registry.command("fuzzy-search")
@click.argument("token")
@click.pass_context
def fuzzy_search(ctx, token):
    return ctx.obj.search_all_repositories(token)
