from unittest import TestCase
from rockerc.rockerc import yaml_dict_to_args


class TestBasicClass(TestCase):

    # Converts dictionary with 'image' and 'args' keys to argument string
    def test_converts_dict_with_image_and_args_to_string(self):
        d = {
            "image": "ubuntu:latest",
            "args": ["x11", "nvidia"],
            "option1": "value1",
            "option2": "value2",
        }
        expected = "--x11 --nvidia --option1 value1--option2 value2ubuntu:latest"
        result = yaml_dict_to_args(d)
        assert result == expected

    def test_empty(self):
        d = {}
        expected = ""
        result = yaml_dict_to_args(d)
        assert result == expected

    def test_realistic(self):

        d = {
            "args": ["nvidia", "x11", "user", "pull", "deps", "git"],
            "image": "ubuntu:22.04",
            "image-name": "$CONTAINER_NAME",
            "name": "$CONTAINER_NAME",
            "volume": '"${PWD}":/workspaces/"${CONTAINER_NAME}":Z',
            "oyr-run-arg": " --detach",
        }

        expected = r'--nvidia --x11 --user --pull --git --image-name "$CONTAINER_NAME" --name "$CONTAINER_NAME" --volume "${PWD}":/workspaces/"${CONTAINER_NAME}":Z --deps --oyr-run-arg " --detach" ubuntu:22.04'

        --nvidia --x11 --user --pull --git --image-name "$CONTAINER_NAME" --name "$CONTAINER_NAME" --volume "${PWD}":/workspaces/"${CONTAINER_NAME}":Z --deps --oyr-run-arg " --detach" ubuntu:22.04'

        --nvidia --x11 --user --pull --deps --git --image-name $CONTAINER_NAME--name $CONTAINER_NAME--volume "${PWD}":/workspaces/"${CONTAINER_NAME}":Z--oyr-run-arg  --detachubuntu:22.04

        result = yaml_dict_to_args(d)
        assert result == expected
