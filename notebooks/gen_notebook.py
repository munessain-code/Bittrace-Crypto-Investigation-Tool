#!/usr/bin/env python3
"""Generate 05_baseline_rf.ipynb as a clean, valid notebook."""

import json

NB = {
    "cells": [],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3.11.0"},
    },
    "nbformat": 4,
    "nbformat_minor": 4,
}

MD = "markdown"
CODE = "code"


def add_md(source):
    NB["cells"].append({"cell_type": MD, "metadata": {}, "source": source, "id": f"md-{len(NB['cells'])}"})


def add_code(source):
    NB["cells"].append({"cell_type": CODE, "execution_count": None, "metadata": {}, "outputs": [], "source": source, "id": f"code-{len(NB['cells'])}"})


# ── Title ──
add_md([
    "# Phase 2: Random Forest Baseline\n",
    "\n",
    "Reproduces the baseline RF classifier from the **Elliptic++** paper (KDD '23).\n",
    "\n",
    "| Step | Transactions | Actors |\n",
    "|---|---|---|\n",
    "| **Preprocessing** | Drop NaN, MinMaxScaler on features | Drop Time step + dupes, MinMaxScaler |\n",
    "| **Unknown class** | Removed (class 3) | Removed (class 3) |\n",
    "| **Labels** | licit(2) -> 0, illicit(1) -> 1 | licit(2) -> 0, illicit(1) -> 1 |\n",
    "| **Split** | Timestep: train < 35, test >= 35 | 70/30 (shuffle=False, rs=15) |\n",
    "| **Model** | RandomForest(n_estimators=50) | RandomForest(n_estimators=50) |\n",
    "| **Features** | 183 features | 56 features |\n",
    "\n",
    "Reference: [Elliptic++ GitHub](https://github.com/git-disl/EllipticPlusPlus)",
])

# ── Setup ──
add_code([
    "import sys, os\n",
    "sys.path.insert(0, '..')\n",
    "\n",
    "import numpy as np\n",
    "import pandas as pd\n",
    "import matplotlib\n",
    "matplotlib.use('Agg')\n",
    "import matplotlib.pyplot as plt\n",
    "import seaborn as sns\n",
    "import logging\n",
    "\n",
    "from sklearn.ensemble import RandomForestClassifier\n",
    "from sklearn.metrics import (\n",
    "    classification_report, confusion_matrix, f1_score,\n",
    "    precision_recall_fscore_support, roc_auc_score, roc_curve,\n",
    ")\n",
    "from sklearn.preprocessing import MinMaxScaler\n",
    "\n",
    "from src.models.baseline import (\n",
    "    load_transaction_features, load_actor_features,\n",
    "    preprocess_transactions, preprocess_actors,\n",
    "    split_transactions, split_actors,\n",
    "    train_rf_transactions, train_rf_actors, ModelResults,\n",
    ")\n",
    "from src.explain.importance import (\n",
    "    get_feature_importance, get_permutation_importance,\n",
    "    get_shap_values, plot_top_features, plot_shap_summary,\n",
    ")\n",
    "\n",
    "logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')\n",
    "RESULTS_DIR = '../docs'\n",
    "os.makedirs(RESULTS_DIR, exist_ok=True)\n",
    "print('Environment loaded')",
])

# ── 1. Data Loading ──
add_md(["## 1. Data Loading & Exploration"])

add_code([
    "tx_raw = load_transaction_features()\n",
    "actor_raw = load_actor_features()\n",
    "\n",
    "print('=== Raw Data ===')\n",
    "print(f'Transactions: {tx_raw.shape[0]:,} rows x {tx_raw.shape[1]} columns')\n",
    "print(f'  Class distribution: {tx_raw[\"class\"].value_counts().sort_index().to_dict()}')\n",
    "print(f'  NaN rows: {tx_raw.isnull().any(axis=1).sum():,}')\n",
    "print()\n",
    "print(f'Actors: {actor_raw.shape[0]:,} rows x {actor_raw.shape[1]} columns')\n",
    "print(f'  Class distribution: {actor_raw[\"class\"].value_counts().sort_index().to_dict()}')\n",
    "print(f'  Duplicate rows: {actor_raw.duplicated().sum():,}')",
])

# ── 2. Preprocessing ──
add_md(["## 2. Preprocessing"])

add_code([
    "tx = preprocess_transactions(tx_raw)\n",
    "print('=== Transactions (after preprocessing) ===')\n",
    "print(f'Shape: {tx.shape}')\n",
    "print(f'Class distribution: {tx[\"class\"].value_counts().to_dict()}')\n",
    "print(f'Illicit ratio: {tx[\"class\"].mean():.3%}')\n",
    "\n",
    "act = preprocess_actors(actor_raw)\n",
    "print()\n",
    "print('=== Actors (after preprocessing) ===')\n",
    "print(f'Shape: {act.shape}')\n",
    "print(f'Class distribution: {act[\"class\"].value_counts().to_dict()}')\n",
    "print(f'Illicit ratio: {act[\"class\"].mean():.3%}')",
])

# ── 3. Splits ──
add_md(["## 3. Train / Test Splits"])

add_code([
    "X_train_tx, X_test_tx, y_train_tx, y_test_tx = split_transactions(tx)\n",
    "print('=== Transaction Splits ===')\n",
    "print(f'Train: {len(X_train_tx):,} ({X_train_tx.shape[1]} features)')\n",
    "print(f'Test:  {len(X_test_tx):,}')\n",
    "print(f'Train illicit ratio: {y_train_tx.mean():.3%}')\n",
    "print(f'Test illicit ratio:  {y_test_tx.mean():.3%}')\n",
    "\n",
    "X_train_act, X_test_act, y_train_act, y_test_act = split_actors(act)\n",
    "print()\n",
    "print('=== Actor Splits ===')\n",
    "print(f'Train: {len(X_train_act):,} ({X_train_act.shape[1]} features)')\n",
    "print(f'Test:  {len(X_test_act):,}')\n",
    "print(f'Train illicit ratio: {y_train_act.mean():.3%}')\n",
    "print(f'Test illicit ratio:  {y_test_act.mean():.3%}')",
])

# ── 4. RF Training: Transactions ──
add_md(["## 4. Random Forest Training - Transactions"])

add_code([
    "tx_results = train_rf_transactions(n_estimators=50, random_state=42)\n",
    "print(tx_results.report)",
])

add_code([
    "cm_tx = confusion_matrix(tx_results.y_test, tx_results.y_pred)\n",
    "fig, ax = plt.subplots(figsize=(6, 5))\n",
    "sns.heatmap(\n",
    "    cm_tx, annot=True, fmt='d', cmap='Blues',\n",
    "    xticklabels=['Licit', 'Illicit'],\n",
    "    yticklabels=['Licit', 'Illicit'],\n",
    "    ax=ax, cbar_kws={'label': 'Count'},\n",
    ")\n",
    "ax.set_xlabel('Predicted')\n",
    "ax.set_ylabel('Actual')\n",
    "ax.set_title('RF - Transactions Confusion Matrix', fontsize=14, fontweight='bold', pad=12)\n",
    "fig.tight_layout()\n",
    "path = os.path.join(RESULTS_DIR, 'confusion_matrix_transactions.png')\n",
    "fig.savefig(path, dpi=150, bbox_inches='tight')\n",
    "plt.close(fig)\n",
    "print(f'Saved: {path}')",
])

# ── 5. RF Training: Actors ──
add_md(["## 5. Random Forest Training - Actors"])

add_code([
    "actor_results = train_rf_actors(n_estimators=50, random_state=42, model_random_state=42)\n",
    "print(actor_results.report)",
])

add_code([
    "cm_act = confusion_matrix(actor_results.y_test, actor_results.y_pred)\n",
    "fig, ax = plt.subplots(figsize=(6, 5))\n",
    "sns.heatmap(\n",
    "    cm_act, annot=True, fmt='d', cmap='Oranges',\n",
    "    xticklabels=['Licit', 'Illicit'],\n",
    "    yticklabels=['Licit', 'Illicit'],\n",
    "    ax=ax, cbar_kws={'label': 'Count'},\n",
    ")\n",
    "ax.set_xlabel('Predicted')\n",
    "ax.set_ylabel('Actual')\n",
    "ax.set_title('RF - Actors Confusion Matrix', fontsize=14, fontweight='bold', pad=12)\n",
    "fig.tight_layout()\n",
    "path = os.path.join(RESULTS_DIR, 'confusion_matrix_actors.png')\n",
    "fig.savefig(path, dpi=150, bbox_inches='tight')\n",
    "plt.close(fig)\n",
    "print(f'Saved: {path}')",
])

# ── 6. Feature Importance: Transactions ──
add_md(["## 6. Feature Importance - Transactions"])

add_code([
    "tx_fi = get_feature_importance(tx_results.model, tx_results.feature_names)\n",
    "print('Top 15 Transaction Features (RF Importance):')\n",
    "print(tx_fi.head(15).to_string(index=False))\n",
    "\n",
    "plot_top_features(\n",
    "    tx_fi, top_n=20,\n",
    "    title='Top 20 Transaction Feature Importances (RF)',\n",
    "    output_path=os.path.join(RESULTS_DIR, 'feature_importance_transactions.png'),\n",
    ")",
])

add_code([
    "tx_perm = get_permutation_importance(\n",
    "    tx_results.model,\n",
    "    X_test_tx.values,\n",
    "    y_test_tx.values,\n",
    "    tx_results.feature_names,\n",
    "    n_repeats=10,\n",
    ")\n",
    "print('Top 15 Transaction Features (Permutation Importance):')\n",
    "print(tx_perm.head(15).to_string(index=False))",
])

# ── 7. Feature Importance: Actors ──
add_md(["## 7. Feature Importance - Actors"])

add_code([
    "act_fi = get_feature_importance(actor_results.model, actor_results.feature_names)\n",
    "print('Top 15 Actor Features (RF Importance):')\n",
    "print(act_fi.head(15).to_string(index=False))\n",
    "\n",
    "plot_top_features(\n",
    "    act_fi, top_n=20,\n",
    "    title='Top 20 Actor Feature Importances (RF)',\n",
    "    output_path=os.path.join(RESULTS_DIR, 'feature_importance_actors.png'),\n",
    ")",
])

add_code([
    "act_perm = get_permutation_importance(\n",
    "    actor_results.model,\n",
    "    X_test_act.values,\n",
    "    y_test_act.values,\n",
    "    actor_results.feature_names,\n",
    "    n_repeats=10,\n",
    ")\n",
    "print('Top 15 Actor Features (Permutation Importance):')\n",
    "print(act_perm.head(15).to_string(index=False))",
])

# ── 8. SHAP ──
add_md(["## 8. SHAP Analysis (optional)"])

add_code([
    "shap_explainer, shap_values, X_shap = get_shap_values(\n",
    "    tx_results.model,\n",
    "    X_test_tx.values,\n",
    "    tx_results.feature_names,\n",
    "    max_samples=500,\n",
    ")\n",
    "\n",
    "if shap_explainer is not None:\n",
    "    plot_shap_summary(\n",
    "        shap_values,\n",
    "        X_shap,\n",
    "        tx_results.feature_names,\n",
    "        output_path=os.path.join(RESULTS_DIR, 'shap_summary_transactions.png'),\n",
    "        max_display=20,\n",
    "    )\n",
    "    print('SHAP summary saved')\n",
    "else:\n",
    "    print('SHAP not available')",
])

# ── 9. ROC Curves ──
add_md(["## 9. ROC Curves"])

add_code([
    "tx_probs = tx_results.model.predict_proba(X_test_tx.values)[:, 1]\n",
    "tx_fpr, tx_tpr, _ = roc_curve(tx_results.y_test, tx_probs)\n",
    "tx_auc = roc_auc_score(tx_results.y_test, tx_probs)\n",
    "\n",
    "act_probs = actor_results.model.predict_proba(X_test_act.values)[:, 1]\n",
    "act_fpr, act_tpr, _ = roc_curve(actor_results.y_test, act_probs)\n",
    "act_auc = roc_auc_score(actor_results.y_test, act_probs)\n",
    "\n",
    "fig, axes = plt.subplots(1, 2, figsize=(14, 6))\n",
    "\n",
    "axes[0].plot(tx_fpr, tx_tpr, color='#3498db', lw=2,\n",
    "             label=f'RF Transactions (AUC={tx_auc:.3f})')\n",
    "axes[0].plot([0, 1], [0, 1], color='gray', lw=1, linestyle='--')\n",
    "axes[0].set_xlabel('False Positive Rate')\n",
    "axes[0].set_ylabel('True Positive Rate')\n",
    "axes[0].set_title('ROC - Transactions')\n",
    "axes[0].legend(loc='lower right')\n",
    "axes[0].grid(True, alpha=0.3)\n",
    "\n",
    "axes[1].plot(act_fpr, act_tpr, color='#e67e22', lw=2,\n",
    "             label=f'RF Actors (AUC={act_auc:.3f})')\n",
    "axes[1].plot([0, 1], [0, 1], color='gray', lw=1, linestyle='--')\n",
    "axes[1].set_xlabel('False Positive Rate')\n",
    "axes[1].set_ylabel('True Positive Rate')\n",
    "axes[1].set_title('ROC - Actors')\n",
    "axes[1].legend(loc='lower right')\n",
    "axes[1].grid(True, alpha=0.3)\n",
    "\n",
    "fig.suptitle('ROC Curves - Random Forest Baseline', fontsize=16, fontweight='bold', y=1.02)\n",
    "fig.tight_layout()\n",
    "path = os.path.join(RESULTS_DIR, 'roc_curves.png')\n",
    "fig.savefig(path, dpi=150, bbox_inches='tight')\n",
    "plt.close(fig)\n",
    "print(f'Saved: {path}')",
])

# ── 10. Paper Comparison ──
add_md(["## 10. Paper Comparison"])

add_code([
    "results = {\n",
    "    'Transactions (our RF)': {\n",
    "        'Precision': round(tx_results.precision, 3),\n",
    "        'Recall':    round(tx_results.recall, 3),\n",
    "        'F1':        round(tx_results.f1, 3),\n",
    "        'AUC-ROC':   round(tx_auc, 3),\n",
    "    },\n",
    "    'Transactions (paper RF)': {\n",
    "        'Precision': 0.986,\n",
    "        'Recall':    0.727,\n",
    "        'F1':        0.833,\n",
    "        'AUC-ROC':   0.986,\n",
    "    },\n",
    "    'Actors (our RF)': {\n",
    "        'Precision': round(actor_results.precision, 3),\n",
    "        'Recall':    round(actor_results.recall, 3),\n",
    "        'F1':        round(actor_results.f1, 3),\n",
    "        'AUC-ROC':   round(act_auc, 3),\n",
    "    },\n",
    "    'Actors (paper RF)': {\n",
    "        'Precision': 0.921,\n",
    "        'Recall':    0.802,\n",
    "        'F1':        0.857,\n",
    "        'AUC-ROC':   0.980,\n",
    "    },\n",
    "}\n",
    "comparison = pd.DataFrame(results).T\n",
    "print('Results Comparison')\n",
    "print(comparison.to_string())",
])

# ── 11. Summary ──
add_md(["## 11. Summary"])

add_code([
    "print('=' * 60)\n",
    "print('PHASE 2 COMPLETE - Random Forest Baseline')\n",
    "print('=' * 60)\n",
    "print()\n",
    "print('Transactions RF:')\n",
    "print(f'   Precision: {tx_results.precision:.3f} | Recall: {tx_results.recall:.3f} | F1: {tx_results.f1:.3f}')\n",
    "print(f'   AUC-ROC: {tx_auc:.3f}')\n",
    "print()\n",
    "print('Actors RF:')\n",
    "print(f'   Precision: {actor_results.precision:.3f} | Recall: {actor_results.recall:.3f} | F1: {actor_results.f1:.3f}')\n",
    "print(f'   AUC-ROC: {act_auc:.3f}')\n",
    "print()\n",
    "print('Output artifacts in docs/')\n",
    "for f in sorted(os.listdir(RESULTS_DIR)):\n",
    "    if f.endswith('.png'):\n",
    "        size = os.path.getsize(os.path.join(RESULTS_DIR, f)) / 1024\n",
    "        print(f'   -> {f} ({size:.0f} KB)')\n",
    "print()\n",
    "print('Next: Phase 3 - GNN models (GraphSAGE, GAT)')\n",
    "print('   Requires approval before proceeding.')",
])

with open('05_baseline_rf.ipynb', 'w') as f:
    json.dump(NB, f, indent=1)

print(f'Generated notebook with {len(NB["cells"])} cells')
