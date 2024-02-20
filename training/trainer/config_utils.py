import argparse
from typing import Type
from typing import TypeVar

from omegaconf import SCMode, OmegaConf

T = TypeVar('T')


def parse_config(config_class: Type[T]) -> T:
    parser = argparse.ArgumentParser()
    parser.add_argument("recipe", type=str)
    namespace, cli_args = parser.parse_known_args()
    config_schema = OmegaConf.structured(config_class)
    config_file = OmegaConf.load(namespace.recipe)
    config_cli_overwrites = OmegaConf.from_cli(args_list=cli_args)
    config_merged = OmegaConf.merge(config_schema, config_file, config_cli_overwrites)
    return OmegaConf.to_container(
        config_merged,
        resolve=True,
        structured_config_mode=SCMode.INSTANTIATE
    )
