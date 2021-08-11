import os
import math
import time
import uuid
import json
import redis
import asyncio
import traceback
import numpy as np

from aredis import StrictRedis
from sanic import Sanic
from sanic import exceptions
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

with open(os.path.join(os.getcwd(), 'config.json')) as file:
    app.ctx.config = json.load(file)

if 'redis' in app.ctx.config:
    app.ctx.redis = redis.Redis(
        host=app.ctx.config['redis']['host'],
        port=app.ctx.config['redis']['port'],
        db=app.ctx.config['redis']['db'],
        password=app.ctx.config['redis']['password'],
        decode_responses=True
    )
    # print(app.ctx.redis.get('tem'))


app.ctx.ar = StrictRedis(host='127.0.0.1', port=6379, db=8)

# todo: setup app.ctx.data = {}, date => dailydata
app.ctx.data = {}

# { request.ctx.user_id => { ws_client_id => queue } }
app.ctx.queues = {}

app.ctx.last_check_points_index = None


async def snapshot_handler(results):

    if all([result['status'] == 'successful'] and result['idx'] == results[0]['idx'] for result in results):
        # todo: notify updates
        check_point_idx = int(results[0]['idx'])
        app.ctx.last_check_points_index = check_point_idx
        print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} snapshotting',
              check_point_idx, results[0])

        await asyncio.gather(*[queue.put({'cmd': 'snapshot', 'idx': check_point_idx, 'date': results[0]['date']}) for queue in sum([list(app.ctx.queues[user_id].values()) for user_id in app.ctx.queues], [])])
        # pass
    else:
        print(f'\n{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}====================== abnormal snapchoting results ======================')
        for result in results:
            print(result)


# before server start
@app.before_server_start
async def setup_dailydata(app, loop):
    # date = time.strftime('%Y%m%d')
    # date = '20210712'
    # app.ctx.data[date] = DailyData(date)
    # print('before server start')
    try:
        today = time.strftime('%Y%m%d')
        app.ctx.data[today] = DailyData(today)

        add_snapshot_handler(snapshot_handler)
        asyncio.create_task(start_snapshot_listening())
    except FileNotFoundError:
        print('there is no running dailydata today')


@app.after_server_start
async def add_snapshotting_handler(app, loop):
    # add_snapshot_handler(snapshot_handler)
    # # asyncio.create_task(start_snapshot_listening())
    # asyncio.create_task(start_snapshot_listening(date='20210712'))
    # print('add snapshotting handler')
    pass


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


async def get_dailydata(date):
    if date not in app.ctx.data:
        try:
            app.ctx.data[date] = DailyData(date)
            add_snapshot_handler(snapshot_handler)
            asyncio.create_task(start_snapshot_listening(date=date))
            print('add snapshotting handler')
        except FileNotFoundError:
            file = os.path.join(os.getcwd(), 'storage', f'{date}.hdf5')
            if os.path.exists(file):
                app.ctx.data[date] = DailyData.load(dt=date)
                if not (await app.ctx.ar.get('hq_assist_count')):
                    assist_count = math.ceil(
                        len(app.ctx.data[date].symbols)/800)+1
                    await app.ctx.ar.set('hq_assist_count', assist_count)
                assist_count = await app.ctx.ar.get('hq_assist_count')

                msg = {
                    'command': 'compute_statistics',
                    'date': date
                }
                await asyncio.gather(
                    *[app.ctx.ar.lpush(f'hq_assist_{_}', json.dumps(msg)) for _ in range(assist_count)]
                )
                results = await asyncio.gather(*[app.ctx.ar.brpop(f'hq_assist_{_}_compute_statistics') for _ in range(assist_count)])
                if not all([json.loads(result[1].decode("utf-8"))['status'] == 'success' for result in results]):
                    raise exceptions.ServerError(
                        f"Failed to calculate statistics for dailydata at ({date})")
            else:
                raise exceptions.NotFound(
                    f"Could not find dailydata at ({date})")

    return app.ctx.data[date]


@app.get("/market/<date:\d{8}>")
async def market(request, date):

    start = time.time()

    dailydata = await get_dailydata(date)

    if "timestamp" in request.args:
        timestamp = float(request.args.get("timestamp"))
    elif app.ctx.last_check_points_index:
        timestamp = int(
            dailydata.check_points[app.ctx.last_check_points_index])
    else:
        timestamp = time.time()

    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp)))

    result = {'date': date, 'timestamp': timestamp, 'check_points': dailydata.check_points.tolist(),
              'request_id': str(request.id)}
    # result = {'date': date, 'timestamp': timestamp}

    if timestamp <= dailydata.check_points[0]:
        check_point_idx = 0
    elif timestamp >= dailydata.check_points[-1]:
        check_point_idx = len(dailydata.check_points)-1
    else:
        check_point_idx = np.argmax(dailydata.check_points > timestamp) - 1

    result['check_point_idx'] = int(check_point_idx)

    result['zs_indices'] = np.argsort(
        dailydata.statistic[check_point_idx, :, 3]).tolist()
    # result['zt_indices'] = np.argwhere(
    #     dailydata.statistic[check_point_idx, :, 4] > 0).flatten().tolist()
    result['zf_indices'] = np.argsort(
        dailydata.statistic[check_point_idx, :, 0]).tolist()
    result['lb_indices'] = np.argsort(
        dailydata.statistic[check_point_idx, :, 2]).tolist()

    result['snapshot'] = dailydata.snapshots[check_point_idx].tolist()
    result['zhangsu'] = dailydata.statistic[check_point_idx, :, 3].tolist()
    result['zhangfu'] = dailydata.statistic[check_point_idx, :, 0].tolist()
    result['liangbi'] = dailydata.statistic[check_point_idx, :, 2].tolist()

    init = request.args.get("init")
    if init:
        file = 'storage//'+date+'_zhishu.json'
        if os.path.exists(file):
            with open(file, 'r') as f:
                result['zhishu'] = json.load(f)
        else:
            tdx = TDX()
            result['zhishu'] = tdx.get_tdx_zhishu()

        result['symbols'] = dailydata.symbols.tolist()
        result['names'] = dailydata.names.tolist()
        result['mcap'] = dailydata.basics[:, 3].tolist()
        result['zt_status'] = list([
            (
                int(idx[0]),
                int(dailydata.check_points[np.argmax(
                    dailydata.statistic[:check_point_idx+1, idx[0], 4] > 0)]),
                dailydata.statistic[check_point_idx, idx[0], 4]
            ) for idx in np.argwhere(dailydata.statistic[check_point_idx, :, 4] > 0)
        ])

    print('market ================>>>', time.time()-start)
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

                    if result['cmd'] == 'snapshot':
                        start = time.time()
                        dailydata = await get_dailydata(result['date'])

                        check_point_idx = result['idx']
                        del result['idx']

                        result['check_point_idx'] = check_point_idx

                        result['zs_indices'] = np.argsort(
                            dailydata.statistic[check_point_idx, :, 3]).tolist()
                        result['zf_indices'] = np.argsort(
                            dailydata.statistic[check_point_idx, :, 0]).tolist()
                        result['lb_indices'] = np.argsort(
                            dailydata.statistic[check_point_idx, :, 2]).tolist()

                        result['snapshot'] = dailydata.snapshots[check_point_idx].tolist()
                        result['zhangsu'] = dailydata.statistic[check_point_idx, :, 3].tolist(
                        )
                        result['zhangfu'] = dailydata.statistic[check_point_idx, :, 0].tolist(
                        )
                        result['liangbi'] = dailydata.statistic[check_point_idx, :, 2].tolist(
                        )

                        # result['zt_indices'] = np.argwhere(dailydata.statistic[check_point_idx, :, 4] > 0).tolist()
                        not_zhangting = dailydata.statistic[check_point_idx-1, :, 4] <= 0
                        zhangting = dailydata.statistic[check_point_idx, :, 4] > 0

                        result['zt_status'] = list([
                            (
                                int(idx[0]),
                                int(dailydata.check_points[np.argmax(
                                    dailydata.statistic[:check_point_idx+1, idx[0], 4] > 0)]) if not_zhangting[idx[0]] else None,
                                dailydata.statistic[check_point_idx, idx[0], 4]
                            ) for idx in np.argwhere(zhangting)
                        ])

                        print('websocket ===============>>>', time.time() -
                              start, np.argwhere(not_zhangting == zhangting))
                        asyncio.create_task(ws.send(json.dumps(result)))

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
            else:
                task.exception()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1234, debug=True)
