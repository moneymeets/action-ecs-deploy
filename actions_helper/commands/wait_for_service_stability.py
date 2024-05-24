from botocore.client import BaseClient


def wait_for_service_stability(ecs_client: BaseClient, cluster: str, service: str):
    # Using Boto3 instead CLI in order to control delay and max attempts, see
    # https://docs.aws.amazon.com/cli/latest/reference/ecs/wait/services-stable.html and
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs/waiter/ServicesStable.html
    ecs_client.get_waiter("services_stable").wait(
        cluster=cluster,
        services=(service,),
        WaiterConfig={
            # Note: The timeout (= delay * max_attempts) must not be shorter than the workflow timeout!
            "Delay": 15,  # seconds to wait between retries
            "MaxAttempts": 1440,
        },
    )
