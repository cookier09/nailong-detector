@echo off
REM 开发者用: 用本机 conda 环境直接跑源码(发布给别人请用打包好的 exe)
cd /d "%~dp0\.."
wmic process where "name='python.exe' and CommandLine like '%%screen_detect.py%%'" call terminate >nul 2>&1
wmic process where "name='pythonw.exe' and CommandLine like '%%screen_detect.py%%'" call terminate >nul 2>&1
start "" "E:\condaData\envs_dirs\yolo-nailong\pythonw.exe" src\screen_detect.py
exit
