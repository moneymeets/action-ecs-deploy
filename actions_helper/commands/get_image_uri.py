import click
from botocore.client import BaseClient


def get_image_uri(ecr_client: BaseClient, ecr_repository: str, tag: str) -> str:
    (image_tag,) = ecr_client.describe_images(
        repositoryName=ecr_repository,
        imageIds=[{"imageTag": tag}],
    )["imageDetails"][0]["imageTags"]

    repository_uri = ecr_client.describe_repositories(
        repositoryNames=[ecr_repository],
    )["repositories"][0]["repositoryUri"]

    image_uri = f"{repository_uri}:{image_tag}"

    click.echo(f"{image_uri=}")

    return image_uri
