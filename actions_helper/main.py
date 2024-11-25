from enum import StrEnum, auto

import boto3
import click

from actions_helper.commands.create_task_definition import create_task_definition
from actions_helper.commands.deregister_task_definition import deregister_task_definition
from actions_helper.commands.get_image_uri import get_image_uri
from actions_helper.commands.run_preflight import run_preflight_container


class Environment(StrEnum):
    DEV = auto()
    TEST = auto()
    LIVE = auto()


@click.group()
def cli():
    pass  # pragma: no cover


@cli.command(
    name="ecs-deploy",
    short_help="Deploy production image to AWS ECS",
)
@click.option("--environment", type=click.Choice(Environment))
@click.option("--allow-feature-branch-deployment", type=bool)
@click.option("--ecr-repository", envvar="ECR_REPOSITORY", type=str)
@click.option("--deployment-tag", envvar="DEPLOYMENT_TAG", type=str)
@click.option("--image-tag", envvar="IMAGE_TAG", type=str)
@click.option("--run-preflight", envvar="RUN_PREFLIGHT", type=bool)
@click.option("--desired-count", type=int)
@click.option("--aws-region", envvar="AWS_DEFAULT_REGION", type=str)
def cmd_ecs_deploy(
    environment: Environment,
    allow_feature_branch_deployment: bool,
    ecr_repository: str,
    deployment_tag: str,
    image_tag: str,
    run_preflight: bool,
    desired_count: str,
    aws_region: str,
):
    if allow_feature_branch_deployment and environment != Environment.DEV:
        raise RuntimeError("Deployments from feature branch only allowed for dev environment")

    ecs_client = boto3.Session(region_name=aws_region).client("ecs")
    ecr_client = boto3.Session(region_name=aws_region).client("ecr")
    service = f"{ecr_repository}-{environment}"
    production_task_definition = local_task_definition = preflight_task_definition = None
    try:
        click.echo("Getting docker image URI...")
        image_uri = get_image_uri(ecr_client=ecr_client, ecr_repository=ecr_repository, tag=image_tag)

        click.echo("Creating local task definition...")
        local_task_definition = create_task_definition(
            ecs_client=ecs_client,
            application_id=f"{ecr_repository}-local-exec-{environment}",
            deployment_tag=deployment_tag,
            image_uri=image_uri,
        )

        click.echo("Creating production task definition...")
        production_task_definition = create_task_definition(
            ecs_client=ecs_client,
            application_id=service,
            deployment_tag=deployment_tag,
            image_uri=image_uri,
        )

        if run_preflight:
            click.echo("Run preflight enabled")
            click.echo("Creating preflight task definition...")
            preflight_task_definition = create_task_definition(
                ecs_client=ecs_client,
                application_id=f"{ecr_repository}-preflight-{environment}",
                deployment_tag=deployment_tag,
                image_uri=image_uri,
            )
            run_preflight_container(
                ecs_client=ecs_client,
                service=service,
                cluster=environment,
                latest_task_definition_arn=preflight_task_definition.latest_task_definition_arn,
            )

        click.echo("Updating service...")
        ecs_client.update_service(
            taskDefinition=production_task_definition.latest_task_definition_arn,
            desiredCount=desired_count,
            cluster=environment,
            service=service,
        )
        click.echo("Service updated")

        click.echo("Waiting for service stability...")
        # Using Boto3 instead CLI in order to control delay and max attempts, see
        # https://docs.aws.amazon.com/cli/latest/reference/ecs/wait/services-stable.html and
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs/waiter/ServicesStable.html
        ecs_client.get_waiter("services_stable").wait(
            cluster=environment,
            services=(service,),
            WaiterConfig={
                # Note: The timeout (= delay * max_attempts) must not be shorter than the workflow timeout!
                "Delay": 2,  # seconds to wait between retries
                "MaxAttempts": 1440,
            },
        )
        click.echo("Service stable")
    finally:
        click.echo("De-registering task definition")
        deregister_task_definition(
            ecs_client=ecs_client,
            cluster=environment,
            service=service,
            production_task_definition_output=production_task_definition,
            local_task_definition_output=local_task_definition,
            preflight_task_definition_output=preflight_task_definition,
            run_preflight=run_preflight,
        )


if __name__ == "__main__":  # pragma: no cover
    cli()
