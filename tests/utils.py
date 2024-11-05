TEST_AWS_DEFAULT_REGION = "us-east-1"
TEST_APPLICATION_ID = "foo"
TEST_CLUSTER = "dev"
TEST_SERVICE = f"{TEST_APPLICATION_ID}-{TEST_CLUSTER}"

TEST_KEYS_TO_DELETE_FROM_TASK_DEFINITION = (
    "taskDefinitionArn",
    "revision",
    "status",
    "compatibilities",
)
