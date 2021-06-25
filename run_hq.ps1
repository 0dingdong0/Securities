# Start-Sleep -Seconds 25

cd D:\workspace\python\Securities

D:\workspace\python\venv_3.9.5\Scripts\activate.ps1
# $env:FORKED_BY_MULTIPROCESSING=1

Start-Sleep -Seconds 1
start-process python run_assists.py

Start-Sleep -Seconds 5
start-process python run_dailydata.py

# Start-Sleep -Seconds 20
# $shell = New-Object -ComObject "Shell.Application"
# $shell.minimizeall()