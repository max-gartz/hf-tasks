import functools
import os
from typing import Dict, Any, List

import fsspec
import numpy as np
import torch
from datasets import Dataset, DatasetDict, IterableDatasetDict
from transformers import (
    Trainer, TrainingArguments,
    AutoModelForSequenceClassification, AutoTokenizer,
    DataCollatorWithPadding, EarlyStoppingCallback,
    EvalPrediction
)

from trainer.callbacks import RemoteSaveCallback
from trainer.config_utils import parse_config
from trainer.configs import Metric
from trainer.configs import TextClassificationTrainingConfig
from trainer.data_utils import get_dataset
from trainer.metrics import (
    BINARY_CLASSIFICATION_METRICS,
    MULTICLASS_CLASSIFICATION_METRICS,
    MULTILABEL_CLASSIFICATION_METRICS
)

torch.set_num_threads(1)


def _get_metrics(problem_type: str, metrics: List[Metric], **kwargs: Any) -> Dict[str, Any]:
    if problem_type == "binary":
        metrics_mapping = BINARY_CLASSIFICATION_METRICS
    elif problem_type == "multiclass":
        metrics_mapping = MULTICLASS_CLASSIFICATION_METRICS
    elif problem_type == "multilabel":
        metrics_mapping = MULTILABEL_CLASSIFICATION_METRICS
    else:
        raise ValueError(f"Invalid problem type: {problem_type}")

    return {
        metric.name: functools.partial(
            metrics_mapping[metric.type],
            **metric.args,
            **kwargs
        )
        for metric in metrics
    }


def main(cfg: TextClassificationTrainingConfig) -> None:
    train_dataset = get_dataset(cfg.train_data, token=cfg.hub_token, seed=cfg.seed)
    dataset_dict_class = DatasetDict if isinstance(train_dataset, Dataset) else IterableDatasetDict
    dataset = dataset_dict_class(train=train_dataset)
    if cfg.eval_data:
        dataset["eval"] = get_dataset(cfg.eval_data, token=cfg.hub_token, seed=cfg.seed)

    num_targets = len(cfg.processing.target)

    if num_targets > 1:
        label2id = {
            label: idx for idx, label
            in enumerate(cfg.processing.target)
        }
        problem_type = "multilabel"
    else:
        label2id = {
            label: idx for idx, label
            in enumerate(dataset["train"].features[cfg.processing.target[0]].names)
        }
        problem_type = "multiclass" if len(label2id) > 2 else "binary"

    id2label = {v: k for k, v in label2id.items()}

    model = AutoModelForSequenceClassification.from_pretrained(
        cfg.model.name_or_path,
        subfolder=cfg.model.subfolder,
        num_labels=len(label2id),
        id2label=id2label,
        label2id=label2id,
        ignore_mismatched_sizes=True,
        trust_remote_code=True,
        token=cfg.hub_token,
        problem_type="multi_label_classification" if problem_type == "multilabel" else None
    )

    tokenizer = AutoTokenizer.from_pretrained(
        cfg.tokenizer.name_or_path,
        subfolder=cfg.tokenizer.subfolder,
        token=cfg.hub_token,
        trust_remote_code=True
    )

    def tokenize(example: Dict[str, Any]) -> Dict[str, Any]:
        if problem_type == "multilabel":
            labels = np.stack(
                [example[k] for k in cfg.processing.target], axis=1, dtype=np.float32
            ).tolist()
        else:
            labels = example[cfg.processing.target[0]]
        return {
            "labels": labels,
            **tokenizer(example[cfg.processing.feature], truncation=True)
        }

    dataset = dataset.map(
        tokenize,
        batched=cfg.processing.batch_size is not None,
        batch_size=cfg.processing.batch_size,
        num_proc=os.cpu_count() if cfg.processing.num_proc == -1 else cfg.processing.num_proc,
        remove_columns=list(set(dataset["train"].column_names) - {"labels"})
    )

    fs = fsspec.filesystem("file")
    if cfg.trainer.remote_storage and ":" in cfg.trainer.remote_storage.output_dir:
        fs = fsspec.filesystem(
            cfg.trainer.remote_storage.output_dir.split(":")[0],
            **cfg.trainer.remote_storage.options
        )

    callbacks = []
    if cfg.trainer.remote_storage:
        callbacks.append(
            RemoteSaveCallback(
                remote_output_dir=cfg.trainer.remote_storage.output_dir,
                fs=fs
            )
        )
    if cfg.trainer.early_stopping:
        callbacks.append(
            EarlyStoppingCallback(
                early_stopping_patience=cfg.trainer.early_stopping.patience,
                early_stopping_threshold=cfg.trainer.early_stopping.threshold,
            )
        )

    training_args = TrainingArguments(
        output_dir=cfg.trainer.output_dir,
        hub_token=cfg.hub_token,
        **cfg.trainer.args
    )

    if cfg.trainer.resume_from_checkpoint:
        if fs.exists(cfg.trainer.resume_from_checkpoint):
            remote_checkpoint = cfg.trainer.resume_from_checkpoint
            fs.get(
                f"{remote_checkpoint}",
                f"{cfg.trainer.output_dir}/",
                recursive=True
            )
            checkpoint_name = remote_checkpoint.split("/")[-1]
            training_args.resume_from_checkpoint = f"{cfg.trainer.output_dir}/{checkpoint_name}"
        else:
            raise FileNotFoundError(
                f"Checkpoint {cfg.trainer.resume_from_checkpoint} not found."
            )

    metrics_kwargs = dict()
    if problem_type == "multilabel":
        metrics_kwargs["num_labels"] = len(label2id)
    elif problem_type == "multiclass":
        metrics_kwargs["num_classes"] = len(label2id)

    metrics = _get_metrics(
        problem_type=problem_type,
        metrics=cfg.metrics,
        **metrics_kwargs
    )

    def compute_metrics(pred: EvalPrediction) -> Dict[str, float]:
        predictions, labels = pred
        return {
            metric: func(
                preds=torch.from_numpy(predictions).type(torch.float32),
                target=torch.from_numpy(labels).type(torch.int32)
            ).round(decimals=5).item()
            for metric, func in metrics.items()
        }

    trainer = Trainer(
        model=model,
        args=training_args,
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
        train_dataset=dataset["train"],
        eval_dataset=dataset.get("eval"),
        tokenizer=tokenizer,
        callbacks=callbacks,
        compute_metrics=compute_metrics
    )
    trainer.train(resume_from_checkpoint=training_args.resume_from_checkpoint)

    if training_args.push_to_hub:
        trainer.push_to_hub(
            commit_message="Update model card.",
            model_name=cfg.model_card.model_name,
            license=cfg.model_card.license,
            language=cfg.model_card.language,
            finetuned_from=cfg.model_card.finetuned_from,
            tasks=cfg.model_card.tasks,
            dataset=cfg.model_card.dataset,
        )
    else:
        trainer.save_model()

    if cfg.trainer.remote_storage:
        fs.put(
            f"{cfg.trainer.output_dir}/*",
            f"{cfg.trainer.remote_storage.output_dir}/",
            overwrite=True
        )


if __name__ == '__main__':
    main(parse_config(config_class=TextClassificationTrainingConfig))
