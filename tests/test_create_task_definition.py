import unittest
from unittest.mock import Mock, patch

import boto3

from actions_helper.commands import create_task_definition as create_task_definition_command
from actions_helper.commands.create_task_definition import create_task_definition, get_rendered_task_definition
from actions_helper.utils import PLACEHOLDER_TEXT
from tests.utils import TEST_APPLICATION_ID


class CreateTaskDefinitionTestCase(unittest.TestCase):
    @patch.object(boto3, attribute="client")
    def setUp(self, boto3_client):
        self.ecs_client = boto3_client
        self.image_uri = "test/dummy:master-e0428b7"

    def _test(self, msg, side_effect):
        with (
            self.subTest(msg),
            self.assertRaises(SystemExit),
            patch.object(self.ecs_client, attribute="describe_task_definition", side_effect=side_effect),
        ):
            get_rendered_task_definition(
                ecs_client=self.ecs_client,
                task_definition_arn=Mock(),
                image_uri=self.image_uri,
            )

    def test_rendered_task_definition_invalid(self):
        self._test(
            msg="Expects exactly one task definition, got empty",
            side_effect=Mock(return_value={"taskDefinition": {"containerDefinitions": []}}),
        )
        self._test(
            msg="Expects exactly one task definition, got multiple",
            side_effect=Mock(
                return_value={
                    "taskDefinition": {"containerDefinitions": [{"image": "dummy1"}, {"image": "dummy2"}]},
                },
            ),
        )
        self._test(
            msg=f"containerDefinitions 'image' not equals to placeholder text - {PLACEHOLDER_TEXT}",
            side_effect=Mock(return_value={"taskDefinition": {"containerDefinitions": [{"image": "dummy"}]}}),
        )

    @patch(
        "actions_helper.commands.create_task_definition.KEYS_TO_DELETE_FROM_TASK_DEFINITION",
        ["foo"],
    )
    def test_rendered_task_definition(self):
        with patch.object(
            self.ecs_client,
            attribute="describe_task_definition",
            side_effect=Mock(
                return_value={"taskDefinition": {"containerDefinitions": [{"image": PLACEHOLDER_TEXT}], "foo": "bar"}},
            ),
        ):
            task_definition = get_rendered_task_definition(
                ecs_client=self.ecs_client,
                task_definition_arn=Mock(),
                image_uri=self.image_uri,
            )

            (replaced_container_definition_image_uri,) = {
                container_definition["image"] for container_definition in task_definition["containerDefinitions"]
            }
            self.assertEqual(replaced_container_definition_image_uri, self.image_uri)
            self.assertNotIn("foo", task_definition.items())

    @patch("actions_helper.commands.create_task_definition.KEYS_TO_DELETE_FROM_TASK_DEFINITION", [])
    @patch("actions_helper.commands.create_task_definition.get_active_task_definition_arn_by_tag", Mock())
    def test_create_task_definition(self):
        with (
            patch.object(
                self.ecs_client,
                attribute="describe_task_definition",
                side_effect=Mock(
                    return_value={
                        "taskDefinition": {"containerDefinitions": [{"image": PLACEHOLDER_TEXT}], "foo": "bar"},
                    },
                ),
            ),
            patch.object(
                self.ecs_client,
                attribute="register_task_definition",
                side_effect=Mock(
                    return_value={"taskDefinition": {"taskDefinitionArn": "deployed_task_definition_arn"}},
                ),
            ),
            patch.object(
                create_task_definition_command,
                attribute="get_active_task_definition_arn_by_tag",
                side_effect=Mock(return_value="test_arn"),
            ),
        ):
            output = create_task_definition(
                ecs_client=self.ecs_client,
                application_id=TEST_APPLICATION_ID,
                image_uri=self.image_uri,
                deployment_tag="GitHub Actions Deployment",
            )
            self.assertEqual(output.previous_task_definition_arn, "test_arn")
            self.assertEqual(output.latest_task_definition_arn, "deployed_task_definition_arn")
