import os
import time
import uuid
import json
import asyncio
import traceback
from sanic import Sanic
from pathlib import Path
from datetime import datetime
from sanic.models.handler_types import RequestMiddlewareType
from websockets.exceptions import ConnectionClosedOK
from asyncio.exceptions import CancelledError

from sanic import response

from libs.tdx import TDX
from libs.dailydata import DailyData
from libs.assist import start_snapshot_listening
from libs.assist import add_snapshot_handler


app = Sanic("My Hello, world app")


app.static("/favicon.ico", "server/static/favicon.png")
app.static("/static", "server/static/")
app.static("/", "server/static/html/index.html")

# todo: setup app.ctx.data = {}, date => dailydata
app.ctx.data = {}

# { request.ctx.user_id => { ws_client_id => queue } }
app.ctx.queues = {}


async def snapshot_handler(results):
    if all([result['status'] == 'successful'] and result['idx'] == results[0]['idx'] for result in results):
        # todo: notify updates
        check_point_idx = int(results[0]['idx'])
        print('snapshotting', check_point_idx)

        await asyncio.gather(*[queue.put({'cmd': 'snapshot', 'idx': check_point_idx}) for queue in sum([list(app.ctx.queues[user_id].values()) for user_id in app.ctx.queues], [])])
        # pass
    else:
        print(f'\n{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}====================== abnormal snapchoting results ======================')
        for result in results:
            print(result)

# before server start


@app.before_server_start
async def setup_dailydata(app, loop):
    # date = time.strftime('%Y%m%d')
    date = '20210712'
    app.ctx.data[date] = DailyData(date)
    print('before server start')


@app.after_server_start
async def add_snapshotting_handler(app, loop):
    add_snapshot_handler(snapshot_handler)
    # asyncio.create_task(start_snapshot_listening())
    asyncio.create_task(start_snapshot_listening(date='20210712'))
    print('add snapshotting handler')

# after server stop


@app.after_server_stop
async def cleanup_dailydata(app, loop):
    print('after_server_stop')


@app.on_request
async def identify_user_id(request):
    if "user_id" in request.cookies:
        request.ctx.user_id = request.cookies.get('user_id')
    else:
        request.ctx.user_id = str(uuid.uuid4())
        app.ctx.queues[request.ctx.user_id] = {}


@app.on_response
async def set_user_id(request, response):
    if "user_id" not in response.cookies:
        response.cookies['user_id'] = request.ctx.user_id


@app.get("/market/<date:\d{8}>")
async def market(request, date):
    
    if date not in app.ctx.data:
        try:
            app.ctx.data[date] = DailyData(date)
        except FileNotFoundError:
            file = os.path.join(os.getcwd(), 'storage', f'{date}.hdf5')
            if os.path.exists(file):
                app.ctx.data[date] = DailyData.load(dt=date)
            else:
                # todo: return error
                pass
            
    dailydata = app.ctx.data[date]

    init = request.args.get("init")
    timestamp = float(request.args.get("timestamp"))

    print(os.getcwd())
    print(init, timestamp)
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp)))

    result = {'date': date, 'request_id': str(request.id)}
    if init:
        result['init'] = True
    
    if timestamp:
        result['timestamp'] = timestamp

    if init is not None:
        file = 'storage//'+date+'_zhishu.json'
        if os.path.exists(file):
            with open('storage//'+time.strftime('%Y%m%d')+'_zhishu.json', 'r') as f:
                result['zhishu'] = json.load(f)
        else:
            tdx = TDX()
            result['zhishu'] = tdx.get_tdx_zhishu()

        result['symbols'] = ''
        result['names'] = ''
        pass

    if timestamp is None:
        ts = time.time()
        pass

    return response.json(result)


@app.get("/kline/<symbol>")
async def kline(request, symbol):
    start_date = request.args.get("start")
    end_date = request.args.get("end")
    return response.text(f'Hello, world! {start_date} {end_date}')


@app.get("/fenshi/<symbol>")
async def fenshi(request, symbol):
    date = request.args.get("ts")
    if date is None:
        date = time.strftime('%Y%m%d')

    ts = request.args.get("ts")
    if ts is None:
        ts = time.time()
    return response.text(f'Hello, world! {date} {ts}')


@app.websocket("/websocket/<ws_client_id>")
async def websocket(request, ws, ws_client_id):
    try:
        print('websocket_client_id:', ws_client_id)
        queue = asyncio.Queue()
        if request.ctx.user_id not in app.ctx.queues:
            app.ctx.queues[request.ctx.user_id] = {}
        app.ctx.queues[request.ctx.user_id][ws_client_id] = queue

        tasks = [
            asyncio.create_task(ws.recv(), name='ws.recv()'),
            asyncio.create_task(queue.get(), name='queue.get()')
        ]

        while True:
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

            tasks = list(pending)

            print('done tasks:')
            for task in done:
                task_name = task.get_name()
                result = task.result()
                print('====', task_name, type(result), result)
                if task_name == 'ws.recv()':
                    tasks.append(asyncio.create_task(
                        ws.recv(), name='ws.recv()'))
                else:
                    tasks.append(asyncio.create_task(
                        queue.get(), name='queue.get()'))
                    asyncio.create_task(ws.send(str(result['idx'])))

            # break
    except Exception as e:
        print(str(e))
        traceback.print_exc()
    finally:
        # remove queue from app.ctx.queues
        del app.ctx.queues[request.ctx.user_id][ws_client_id]
        # cancel running tasks
        for task in tasks:
            if not task.done():
                task.cancel()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1234, debug=True)
