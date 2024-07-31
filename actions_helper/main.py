import os

import boto3
import click

from actions_helper.commands.get_active_task_definition_by_tag import get_active_task_definition_arn_by_tag
from actions_helper.commands.wait_for_service_stability import wait_for_service_stability
from actions_helper.commands.wait_for_task_stopped import wait_for_task_stopped


@click.group()
def cli():
    pass


@cli.command(name="wait-for-service-stability")
@click.option("--aws-region", default=os.environ.get("AWS_DEFAULT_REGION"), type=str)
@click.option("--cluster", type=str)
@click.option("--service", type=str)
def cmd_wait_for_service_stability(
    aws_region: str,
    cluster: str,
    service: str,
):
    wait_for_service_stability(
        ecs_client=boto3.Session(region_name=aws_region).client("ecs"),
        cluster=cluster,
        service=service,
    )


@cli.command(name="wait-for-task-stopped")
@click.option("--aws-region", default=os.environ.get("AWS_DEFAULT_REGION"), type=str)
@click.option("--cluster", type=str)
@click.option("--task", type=str)
def cmd_wait_for_task_stopped(
    aws_region: str,
    cluster: str,
    task: str,
):
    wait_for_task_stopped(
        ecs_client=boto3.Session(region_name=aws_region).client("ecs"),
        cluster=cluster,
        task=task,
    )


@cli.command(
    name="get-active-task-definition-arn-by-tag",
    short_help="Get active task definition ARN  by specified tags",
)
@click.option("--application-id", default=os.environ.get("APPLICATION_ID"), type=str)
@click.option("--tags", default=os.environ.get("TAGS"), type=str)
@click.option("--aws-region", default=os.environ.get("AWS_DEFAULT_REGION"), type=str)
@click.option("--allow-initial-deployment", is_flag=True, default=False)
def cmd_get_active_task_definition_arn_by_tag(
    application_id: str,
    tags: str,
    aws_region: str,
    allow_initial_deployment: bool,
):
    click.echo(
        get_active_task_definition_arn_by_tag(
            ecs_client=boto3.Session(region_name=aws_region).client("ecs"),
            task_definition_family_prefix=application_id,
            task_definition_tags=tags,
            allow_initial_deployment=allow_initial_deployment,
        ),
    )


if __name__ == "__main__":
    cli()
