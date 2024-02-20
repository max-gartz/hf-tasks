from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any

from omegaconf import MISSING
from trainer.metrics import ClassificationMetric


@dataclass
class HFDataset:
    name_or_path: str = MISSING
    split: str = MISSING
    config_name: Optional[str] = None
    revision: str = "main"
    rename_columns: Dict[str, str] = field(default_factory=dict)
    num_proc: Optional[int] = None
    streaming: bool = False
    shuffle: bool = True
    buffer_size: int = 1000


class StoppingStrategy(str, Enum):
    first_exhausted = "first_exhausted"
    all_exhausted = "all_exhausted"


@dataclass
class HFModel:
    name_or_path: str = MISSING
    subfolder: str = ""


@dataclass
class HFTokenizer:
    name_or_path: str = MISSING
    subfolder: str = ""


@dataclass
class RemoteStorage:
    output_dir: str = MISSING
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EarlyStopping:
    patience: int = 3
    threshold: float = 0.001


@dataclass
class HFTrainer:
    output_dir: str = MISSING
    remote_storage: Optional[RemoteStorage] = None
    early_stopping: Optional[EarlyStopping] = None
    resume_from_checkpoint: Optional[str] = None
    args: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HFModelCard:
    update: bool = False
    language: Optional[str] = None
    license: Optional[str] = None
    model_name: Optional[str] = None
    finetuned_from: Optional[str] = None
    tasks: Optional[List[str]] = None
    dataset: Optional[List[str]] = None


@dataclass
class Metric:
    name: str
    type: ClassificationMetric
    args: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Processing:
    batch_size: Optional[int] = None
    num_proc: Optional[int] = None
    feature: str = "text"
    target: List[str] = field(default_factory=lambda: ["label"])


@dataclass
class TextClassificationTrainingConfig:
    model: HFModel = HFModel()
    tokenizer: HFTokenizer = HFTokenizer()
    train_data: HFDataset = HFDataset()
    eval_data: Optional[HFDataset] = None
    processing: Processing = Processing()
    trainer: HFTrainer = HFTrainer()
    model_card: HFModelCard = HFModelCard()
    seed: Optional[int] = None
    hub_token: Optional[bool] = None
    metrics: List[Metric] = field(default_factory=list)
