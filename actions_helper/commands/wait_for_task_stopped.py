from botocore.client import BaseClient


def wait_for_task_stopped(ecs_client: BaseClient, cluster: str, task: str):
    # Using Boto3 instead CLI in order to control delay and max attempts, see
    # https://docs.aws.amazon.com/cli/latest/reference/ecs/wait/tasks-stopped.html and
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs/waiter/TasksStopped.html
    ecs_client.get_waiter("tasks_stopped").wait(
        cluster=cluster,
        tasks=(task,),
        WaiterConfig={
            # Note: The timeout (= delay * max_attempts) must not be shorter than the workflow timeout!
            "Delay": 2,  # seconds to wait between retries
            "MaxAttempts": 1440,
        },
    )
