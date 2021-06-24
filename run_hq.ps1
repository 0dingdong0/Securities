# Start-Sleep -Seconds 25

cd D:\workspace\python\Securities

D:\workspace\python\venv_3.9.5\Scripts\activate.ps1
# $env:FORKED_BY_MULTIPROCESSING=1

Start-Sleep -Seconds 3
start-process celery -ArgumentList "beat -A libs.CeleryTasks.schedule -l info --pidfile="
# start-process flower -ArgumentList "--port=5555 --broker=redis://localhost:6379/0 --broker_api=redis://localhost:6379/0"

Start-Sleep -Seconds 10
start-process celery -ArgumentList "worker -A libs.CeleryTasks.routine_tasks -c 5 -l info -Q eyelashes_p4p,celery --purge -n Eyelashes[p4p]@localhost"
start-process celery -ArgumentList "worker -A libs.CeleryTasks.routine_tasks -c 3 -l info -Q tools_p4p,celery --purge -n Tools[p4p]@localhost"

Start-Sleep -Seconds 10
start-process celery -ArgumentList "worker -A libs.CeleryTasks.sub_tasks -c 1 -l info -Q eyelashes_inquiry_carrie --purge -n Eyelashes[inquiry]:Carrie@localhost"
start-process celery -ArgumentList "worker -A libs.CeleryTasks.sub_tasks -c 1 -l info -Q tools_inquiry_jessica --purge -n Tools[inquiry]:Jessica@localhost"

Start-Sleep -Seconds 10
start-process celery -ArgumentList "worker -A libs.CeleryTasks.sub_tasks -c 1 -l info -Q eyelashes_inquiry_ada --purge -n Eyelashes[inquiry]:Ada@localhost"
start-process celery -ArgumentList "worker -A libs.CeleryTasks.sub_tasks -c 1 -l info -Q eyelashes_inquiry_jodi --purge -n Eyelashes[inquiry]:Jodi@localhost"
# start-process celery -ArgumentList "worker -A libs.CeleryTasks.sub_tasks -c 1 -l info -Q eyelashes_inquiry_jianwei --purge -n Eyelashes[inquiry]:Jianwei@localhost"

Start-Sleep -Seconds 15
start-process celery -ArgumentList "worker -A libs.CeleryTasks.sub_tasks -c 1 -l info -Q tools_inquiry_carrie --purge -n Tools[inquiry]:Carrie@localhost"
start-process celery -ArgumentList "worker -A libs.CeleryTasks.sub_tasks -c 1 -l info -Q tools_inquiry_helen --purge -n Tools[inquiry]:Helen@localhost"

Start-Sleep -Seconds 20
$shell = New-Object -ComObject "Shell.Application"
$shell.minimizeall()