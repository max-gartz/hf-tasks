from typing import Any

import fsspec
from transformers.trainer_callback import TrainerCallback, TrainerControl, TrainerState
from transformers.training_args import TrainingArguments


class RemoteSaveCallback(TrainerCallback):
    def __init__(
            self,
            remote_output_dir: str,
            fs: fsspec.AbstractFileSystem = fsspec.filesystem("file")
    ) -> None:
        self.remote_output_dir = remote_output_dir
        self.fs = fs
        self.fs.makedirs(self.remote_output_dir, exist_ok=True)

    def on_save(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        **kwargs: Any
    ) -> None:
        self.fs.put(
            f"{args.output_dir}/checkpoint-{state.global_step}/",
            f"{self.remote_output_dir}/checkpoint-{state.global_step}/",
            recursive=True,
            overwrite=True
        )
