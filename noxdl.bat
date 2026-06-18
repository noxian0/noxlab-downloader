@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
title NoxLab Downloader
mode con: cols=132 lines=42 >nul 2>nul
python "%~dp0downloader.py" %*
