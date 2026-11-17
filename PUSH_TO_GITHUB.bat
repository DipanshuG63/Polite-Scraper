@echo off
setlocal
cd /d "%~dp0"
echo ==========================================
echo W5 Polite Scraper - Public GitHub Push
 echo ==========================================
echo.
echo Before running this, create an EMPTY PUBLIC repository named polite-scraper:
echo https://github.com/new
echo Do not add a README or .gitignore during creation.
echo.
where git >nul 2>&1
if errorlevel 1 (
    echo ERROR: Git was not found. Install Git for Windows or run from Git Bash.
    pause
    exit /b 1
)
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
    echo ERROR: This project is missing its .git history. Extract the complete ZIP first.
    pause
    exit /b 1
)
git remote get-url origin >nul 2>&1
if errorlevel 1 (
    git remote add origin https://github.com/DipanshuG63/polite-scraper.git
) else (
    git remote set-url origin https://github.com/DipanshuG63/polite-scraper.git
)
if errorlevel 1 goto :push_failed

echo.
echo Pushing all existing stage commits to your separate repository...
git push -u origin main
if errorlevel 1 goto :push_failed

echo.
echo SUCCESS: Push finished.
echo Submission URL: https://github.com/DipanshuG63/polite-scraper
git log --oneline -9
goto :done

:push_failed
echo.
echo PUSH FAILED. Confirm the new repo exists and that GitHub authentication succeeded.
echo The local project and all commits are still safe.

:done
echo.
pause
endlocal
