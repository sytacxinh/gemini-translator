@echo off
title Push to GitHub
cd /d "%~dp0"

echo ========================================================
echo Auto Push to GitHub
echo ========================================================
echo.

echo [1/3] Adding files...
git add -A

echo.
echo Current Status:
git status
echo.

:: Ask for commit message
set /p commit_msg="Enter commit message (Press Enter for 'Auto update'): "
if "%commit_msg%"=="" set commit_msg=Auto update

echo.
echo [2/3] Committing...
git commit -m "%commit_msg%"

echo.
echo [3/3] Pushing...
git push

echo.
echo ========================================================
echo DONE!
pause