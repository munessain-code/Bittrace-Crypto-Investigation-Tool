#!/usr/bin/env python3
"""Download Elliptic++ dataset CSVs.

The dataset is hosted on Google Drive. This script tries gdown first,
then provides manual fallback instructions.

Files to download:
  - txs_features.csv      (183 features per transaction)
  - txs_classes.csv       (class labels: 1=illicit, 2=licit, 3=unknown)
  - txs_edgelist.csv      (tx-to-tx money flow edges)
  - wallets_features.csv  (56 features per wallet)
  - wallets_classes.csv   (class labels)
  - AddrAddr_edgelist.csv (addr-to-addr interaction edges)
  - AddrTx_edgelist.csv   (addr-to-tx edges)
  - TxAddr_edgelist.csv   (tx-to-addr edges)

Dataset folder: https://drive.google.com/drive/folders/1MRPXz79Lu_JGLlJ21MDfML44dKN9R08l
"""

import argparse
import os
import sys

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

EXPECTED_FILES = [
    "txs_features.csv",
    "txs_classes.csv",
    "txs_edgelist.csv",
    "wallets_features.csv",
    "wallets_classes.csv",
    "AddrAddr_edgelist.csv",
    "AddrTx_edgelist.csv",
    "TxAddr_edgelist.csv",
]

# Google Drive folder ID
FOLDER_ID = "1MRPXz79Lu_JGLlJ21MDfML44dKN9R08l"


def check_existing():
    """Return list of files already present in data/."""
    existing = []
    for fname in EXPECTED_FILES:
        path = os.path.join(DATA_DIR, fname)
        if os.path.exists(path):
            size = os.path.getsize(path) / (1024 * 1024)
            existing.append((fname, size))
        else:
            existing.append((fname, None))
    return existing


def download_with_gdown():
    """Attempt to download individual files via gdown."""
    try:
        import gdown
    except ImportError:
        print("gdown not installed. Run: uv pip install gdown")
        return False

    # Individual file IDs would need to be looked up from the Drive folder.
    # Since the folder contains subfolders, we need the direct file IDs.
    # For now, download the zip if available or guide manual download.
    print("Note: gdown can download individual files if you have direct file IDs.")
    print("The dataset is organized in subfolders on Google Drive.")
    print()
    print("Recommended approach: manually download from the folder,")
    print("then place CSVs in this directory.")
    return False


def print_manual_instructions():
    """Print clear manual download instructions."""
    print("=" * 60)
    print("ELLIPIC++ DATASET — MANUAL DOWNLOAD")
    print("=" * 60)
    print()
    print("1. Open: https://drive.google.com/drive/folders/1MRPXz79Lu_JGLlJ21MDfML44dKN9R08l")
    print()
    print("2. Download each subfolder's CSV files:")
    print("   - Transactions/ -> txs_features.csv, txs_classes.csv, txs_edgelist.csv")
    print("   - Actors/       -> wallets_features.csv, wallets_classes.csv")
    print("   - Edges/        -> AddrAddr_edgelist.csv, AddrTx_edgelist.csv, TxAddr_edgelist.csv")
    print()
    print("3. Place all CSV files in:")
    print(f"   {DATA_DIR}/")
    print()
    print("4. Run this script again to verify all files are present.")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Download and verify Elliptic++ dataset")
    parser.add_argument(
        "--download", action="store_true",
        help="Attempt automatic download (manual fallback recommended)",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Only check which files are present",
    )
    args = parser.parse_args()

    status = check_existing()

    if args.check:
        print("Elliptic++ Dataset Status:")
        print("-" * 50)
        all_present = True
        for fname, size in status:
            if size is not None:
                print(f"  ✓ {fname:<30} ({size:.1f} MB)")
            else:
                print(f"  ✗ {fname:<30} MISSING")
                all_present = False
        print("-" * 50)
        if all_present:
            print("All files present! ✓")
        else:
            print("Some files missing — see download instructions below.")
            print()
            print_manual_instructions()
        return

    if args.download:
        success = download_with_gdown()
        if not success:
            print_manual_instructions()
        return

    # Default: check status and show instructions if needed
    missing = [fname for fname, size in status if size is None]
    if missing:
        print(f"Missing {len(missing)}/{len(EXPECTED_FILES)} dataset files.")
        print()
        print_manual_instructions()
    else:
        print("All Elliptic++ dataset files present! ✓")
        for fname, size in status:
            print(f"  {fname:<30} ({size:.1f} MB)")


if __name__ == "__main__":
    main()
