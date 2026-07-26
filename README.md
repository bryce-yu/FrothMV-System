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

After completing a meaningful change:

```powershell
git status
git add .
git commit -m "Describe the completed change"
```

View recent commits:

```powershell
git log --oneline
```