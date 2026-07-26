# Dataset setup

The full Kaggle froth-bubble segmentation dataset is not stored in this
repository because of its size.

Store it locally outside OneDrive and Git, then set the environment variable:

```powershell
setx FROTH_DATASET_ROOT "C:\path\to\froth-bubbles-dataset"

Restart VS Code after setting the variable.

Project scripts access the dataset through FROTH_DATASET_ROOT.