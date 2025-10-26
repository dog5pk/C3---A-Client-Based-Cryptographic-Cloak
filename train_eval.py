#!/usr/bin/env python3
"""
Training and evaluation script for website-fingerprinting classification.

Given a CSV file of features extracted by `feature_extractor.py`, this
script trains a RandomForest classifier using scikit-learn, evaluates
its performance on a hold-out test set, and produces a simple report
including precision, recall and confusion matrix.  It also draws a
receiver-operator characteristic (ROC) curve for the micro-averaged
classifier and saves it to disk.

This script is intended for offline experiments with small datasets
(e.g., 100 sites).  For reproducibility, a fixed random seed is used.

Requirements: pandas, numpy, scikit-learn, matplotlib.  Install via:

    pip install pandas numpy scikit-learn matplotlib
"""

import argparse
import os
import sys
from typing import Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, label_binarize
from sklearn.metrics import classification_report, confusion_matrix, roc_curve, auc
import matplotlib.pyplot as plt


def load_dataset(csv_path: str) -> Tuple[pd.DataFrame, np.ndarray, LabelEncoder]:
    """Load features and labels from CSV and encode labels."""
    df = pd.read_csv(csv_path)
    if "label" not in df.columns:
        raise ValueError("CSV must contain a 'label' column")
    labels = df["label"].values
    X = df.drop(columns=["label"]).values
    le = LabelEncoder()
    y = le.fit_transform(labels)
    return X, y, le


def train_model(X: np.ndarray, y: np.ndarray) -> RandomForestClassifier:
    """Train a RandomForest classifier on the provided data."""
    clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    clf.fit(X, y)
    return clf


def evaluate_model(
    clf: RandomForestClassifier,
    X_test: np.ndarray,
    y_test: np.ndarray,
    le: LabelEncoder,
    output_dir: str,
) -> None:
    """Evaluate the model and produce an evaluation report and ROC plot."""
    y_pred = clf.predict(X_test)
    # Classification report
    report = classification_report(y_test, y_pred, target_names=le.classes_, digits=4)
    print("=== Classification report ===")
    print(report)
    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    print("=== Confusion matrix ===")
    print(cm)
    # ROC curve (micro average) if classifier supports probability output
    try:
        y_score = clf.predict_proba(X_test)
    except AttributeError:
        print("[warn] classifier does not support probability estimates; skipping ROC plot")
        return
    # Binarize labels for multiclass ROC
    y_test_bin = label_binarize(y_test, classes=np.arange(len(le.classes_)))
    # Compute micro-average ROC curve and AUC
    fpr, tpr, _ = roc_curve(y_test_bin.ravel(), y_score.ravel())
    roc_auc = auc(fpr, tpr)
    # Plot
    plt.figure()
    plt.plot(fpr, tpr, color="darkorange", lw=2, label=f"micro-average ROC curve (area = {roc_auc:.2f})")
    plt.plot([0, 1], [0, 1], color="navy", lw=2, linestyle="--")
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("Receiver Operating Characteristic")
    plt.legend(loc="lower right")
    os.makedirs(output_dir, exist_ok=True)
    roc_path = os.path.join(output_dir, "roc_curve.png")
    plt.savefig(roc_path)
    print(f"ROC curve saved to {roc_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and evaluate website fingerprinting classifier")
    parser.add_argument("features_csv", help="Path to CSV file produced by feature_extractor.py")
    parser.add_argument("--output_dir", default="evaluation", help="Directory to save evaluation outputs")
    parser.add_argument("--test_size", type=float, default=0.2, help="Fraction of data to use for the test set")
    args = parser.parse_args()
    X, y, le = load_dataset(args.features_csv)
    # Split dataset
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=args.test_size,
        random_state=42,
        stratify=y,
    )
    # Train model
    clf = train_model(X_train, y_train)
    # Evaluate
    evaluate_model(clf, X_test, y_test, le, args.output_dir)


if __name__ == "__main__":
    main()
