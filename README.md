# Froth MV Supervisory System

Python-based machine vision edge analytics system for extracting froth flotation bubble metrics and providing supervisory variables for industrial automation integration.

## Project Structure

```text
dataset/        Froth images, masks and reduced datasets
documentation/  Diagrams, notes and screenshots
models/         YOLOv8 model files and weights
results/        Generated images, metrics and test outputs
src/            Python source code
tests/          Test scripts
requirements.txt
```

## Python Environment

The project folder is stored in OneDrive, but each laptop uses its own virtual environment outside OneDrive.

Local environment location:

```text
C:\PythonEnvironments\FrothMV-venv
```

Create the environment on each laptop:

```powershell
New-Item -ItemType Directory -Force C:\PythonEnvironments
python -m venv C:\PythonEnvironments\FrothMV-venv
```

Activate it:

```powershell
C:\PythonEnvironments\FrothMV-venv\Scripts\Activate.ps1
```

Install the saved dependencies:

```powershell
pip install -r requirements.txt
```

In VS Code, select:

```text
C:\PythonEnvironments\FrothMV-venv\Scripts\python.exe
```

When a dependency is added or updated, regenerate the dependency file:

```powershell
pip freeze > requirements.txt
```

## Verify the Environment

```powershell
python -c "import cv2, numpy, pandas, matplotlib, scipy, ultralytics; print('Environment working')"
```

## Git Workflow

The project folder is currently synchronised through OneDrive and also connected to GitHub.

To avoid conflicts:

- Do not edit the project on both laptops at the same time.
- Allow OneDrive to finish syncing before opening the project on the other laptop.
- Check Git status before committing, pulling or pushing.
- Do not commit the full dataset, virtual environments or large generated outputs.

### Starting work

Open the project in VS Code, activate the required environment, then run:

```powershell
git status
git pull
```

### Saving completed work

After completing a meaningful task:

```powershell
git status
git add <files-to-commit>
git commit -m "Brief description of completed work"
git push
```

Prefer adding specific files rather than using git add . without checking what will be included.

### Switching laptops

Before stopping work on one laptop:
```powershell
git status
git push
```

Wait for OneDrive to finish syncing.

On the other laptop:

```powershell
git status
git pull
```

Then activate the appropriate Python environment.

### Dataset handling

The full Kaggle froth dataset is stored locally outside OneDrive and Git.

Each laptop accesses its local dataset copy through:

```text
FROTH_DATASET_ROOT
```

The repository stores only code, documentation, configuration files, manifests and lightweight results.

## Run the MV pipeline

Process one image:

```powershell
python src/run_single_image.py path\to\image.png
```

Process a folder:

```powershell
python src/run_folder_pipeline.py path\to\image_folder
```