@echo off
set ELECTRON_RUN_AS_NODE=
set NODE_ENV=development
"%~dp0..\..\node_modules\electron\dist\electron.exe" "%~dp0"
