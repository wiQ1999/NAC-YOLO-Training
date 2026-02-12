# NAC YOLO Training

This repository contains the core research pipeline used in a Master's thesis on lunar crater detection with YOLOv8 under image degradations.

## Project Goal

Evaluate how crater detection quality changes under different degradation types:

- `blur`
- `downsampling`
- `summation` (crosstrack summation simulation)
- `all` (randomly one of the above)

## Repository Structure

- `tools/` - Python scripts for data preparation, labeling, splitting, and analysis.
- `bash/` - Bash scripts for NAC EDR (`.IMG`) to GeoTIFF processing.
- `colab/train_model.ipynb` - main notebook for tuning, training, validation, and inference.
- `data/` - raw and intermediate processing data (EDR, GeoTIFF, tiles, labels).
- `datasets/` - ready YOLO datasets (`train/val/test`, `HQ_test`, `LQ_test`).
- `runs/` - training/validation outputs (weights, metrics, plots, confusion matrices).
- `img/` - thesis figures and qualitative prediction examples.

## Main Experiments

Training runs in `runs/detect/`:

- `300m_with_test_tuned` (baseline)
- `300m_with_test_tuned_blur`
- `300m_with_test_tuned_downsampling`
- `300m_with_test_tuned_summation`
- `300m_with_test_tuned_all`

Validation results are stored in `runs/detect/val/` for both `HQ` and `LQ` domains.
