from torchmetrics.functional import classification
from enum import Enum


class ClassificationMetric(str, Enum):
    accuracy = "accuracy"
    precision = "precision"
    recall = "recall"
    f1 = "f1"
    auroc = "auroc"


BINARY_CLASSIFICATION_METRICS = dict(
    accuracy=classification.binary_accuracy,
    precision=classification.binary_precision,
    recall=classification.binary_recall,
    f1=classification.binary_f1_score,
    auroc=classification.binary_auroc
)

MULTICLASS_CLASSIFICATION_METRICS = dict(
    accuracy=classification.multiclass_accuracy,
    precision=classification.multiclass_precision,
    recall=classification.multiclass_recall,
    f1=classification.multiclass_f1_score,
    auroc=classification.multiclass_auroc
)

MULTILABEL_CLASSIFICATION_METRICS = dict(
    accuracy=classification.multilabel_accuracy,
    precision=classification.multilabel_precision,
    recall=classification.multilabel_recall,
    f1=classification.multilabel_f1_score,
    auroc=classification.multilabel_auroc
)
