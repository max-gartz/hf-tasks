import os
from typing import Optional

import datasets
from datasets import Dataset, IterableDataset

from trainer.configs import HFDataset


def get_dataset(
        config: HFDataset,
        token: Optional[bool] = None,
        seed: Optional[int] = None
) -> Dataset | IterableDataset:
    num_proc = os.cpu_count() if config.num_proc == -1 else config.num_proc

    ds = datasets.load_dataset(
        path=config.name_or_path,
        name=config.config_name,
        split=config.split,
        revision=config.revision,
        streaming=config.streaming,
        num_proc=num_proc,
        token=token
    ).rename_columns(column_mapping=config.rename_columns)

    if config.shuffle:
        if isinstance(ds, Dataset):
            ds = ds.shuffle(seed=seed).flatten_indices(num_proc=num_proc)
        else:
            ds = ds.shuffle(buffer_size=config.buffer_size, seed=seed)
    return ds
