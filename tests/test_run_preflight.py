import unittest
from unittest.mock import Mock, patch

import boto3

from actions_helper.commands.run_preflight import run_preflight_container
from tests.utils import TEST_CLUSTER, TEST_SERVICE


def patch_services(*arg, **kwarg):
    return {
        "services": [
            {
                "networkConfiguration": {
                    "awsvpcConfiguration": {"subnets": ["subnet.id"], "securityGroups": ["security_group.id"]},
                },
            },
        ],
    }


class RunPreflightTestCase(unittest.TestCase):
    @patch.object(boto3, attribute="client")
    def setUp(self, boto3_client):
        self.ecs_client = boto3_client

    def test_failed_run_preflight(self):
        def patch_task_container_to_fail(*arg, **kwarg):
            return {"tasks": [{"containers": [{"exitCode": 1, "reason": "curl command not found"}]}]}

        with (
            self.subTest("Failed preflight"),
            patch.object(self.ecs_client, attribute="describe_services", side_effect=patch_services),
            patch.object(self.ecs_client, attribute="describe_tasks", side_effect=patch_task_container_to_fail),
            self.assertRaises(SystemExit),
        ):
            run_preflight_container(
                ecs_client=self.ecs_client,
                cluster=TEST_CLUSTER,
                service=TEST_SERVICE,
                latest_task_definition_arn=Mock(),
            )

    def test_run_preflight(self):
        def patch_task_container(*arg, **kwarg):
            return {"tasks": [{"containers": [{"exitCode": 0, "reason": ""}]}]}

        with (
            self.subTest("Successful preflight"),
            patch.object(self.ecs_client, attribute="describe_services", side_effect=patch_services),
            patch.object(self.ecs_client, attribute="describe_tasks", side_effect=patch_task_container),
        ):
            run_preflight_container(
                ecs_client=self.ecs_client,
                cluster=TEST_CLUSTER,
                service=TEST_SERVICE,
                latest_task_definition_arn=Mock(),
            )
