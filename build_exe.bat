@echo off
title Build AI Translator EXE
cd /d "%~dp0"

echo ========================================================
echo Calling AI Translator v1.5.0...
echo Please wait, this process takes approximately 1-2 minutes.
echo ========================================================
echo.

python -m PyInstaller AITranslator.spec --clean --noconfirm

echo.
echo ========================================================
echo DONE! Check the exe file in the 'dist/' folder
pause