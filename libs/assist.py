import time
import math
import json
import redis
import asyncio
import traceback
import numpy as np
from datetime import datetime
from aredis import StrictRedis
from multiprocessing import Process

from libs.quotation import Quotation
from libs.dailydata import DailyData
from libs.utils import Utils
from libs.cython.compute import compute_stats

rd = redis.Redis(host='127.0.0.1', port=6379, db=8)
ar = StrictRedis(host='127.0.0.1', port=6379, db=8)

snapshot_handlers = []


def assist(assist_idx, assist_count):

    data = {}

    def get_daily_data(date):
        if date not in data:
            dd = DailyData(date, create=False)
            group_size = math.ceil(len(dd.symbols)/assist_count)
            scope = (
                assist_idx*group_size,
                min((assist_idx+1)*group_size, len(dd.symbols))
            )
            data[date] = (dd, scope)

        return data[date]

    def compute_statistics(date):
        dd, scope = get_daily_data(date)
        basics = dd.basics[scope[0]:scope[1], :]
        for _, check_point in enumerate(dd.check_points):

            snapshot = dd.snapshots[_, scope[0]:scope[1], :]
            statistic = dd.statistic[_, scope[0]:scope[1], :]

            time_lapse = dd.get_time_lapse(_)
            ma5pm_anchor_idx = dd.get_ma5pm_anchor_idx(_)
            fs5p = dd.snapshots[ma5pm_anchor_idx, scope[0]:scope[1], :]

            compute_stats(snapshot, basics, statistic, fs5p, time_lapse)

    async def snapshotting(date):
        try:
            dd, scope = get_daily_data(date)

            q = Quotation(symbols=dd.symbols.tolist()[scope[0]:scope[1]])
            basics = dd.basics[scope[0]:scope[1], :]

            for _, check_point in enumerate(dd.check_points):
                if time.time() > check_point:
                    continue

                delay = (check_point-time.time())
                await asyncio.sleep(max(delay, 0))

                try:
                    await q.snapshot(array=dd.snapshots[_, scope[0]:scope[1], :])

                    snapshot = dd.snapshots[_, scope[0]:scope[1], :]
                    statistic = dd.statistic[_, scope[0]:scope[1], :]

                    time_lapse = dd.get_time_lapse(_)
                    ma5pm_anchor_idx = dd.get_ma5pm_anchor_idx(_)
                    fs5p = dd.snapshots[ma5pm_anchor_idx, scope[0]:scope[1], :]

                    compute_stats(snapshot, basics,
                                  statistic, fs5p, time_lapse)

                    await ar.publish(f'hq_assist_{assist_idx}_snapshotting', json.dumps({"status": 'successful', "idx": _, 'check_point': int(check_point)}))

                except Exception as e:
                    error = {
                        "status": 'failed',
                        "idx": _,
                        'check_point': int(check_point),
                        "exception": str(e),
                        'traceback': traceback.format_exc()
                    }
                    await ar.publish(f'hq_assist_{assist_idx}_snapshotting', json.dumps(error))

                # finally:
                #     # 在这个地方进行增量存盘，会导致存盘数据不完整，因为不能确定最后一个完成当前 snapshot 的 assist
                #     if assist_idx == 0:
                #         dd.incremental_save(_)

        finally:
            await q.exit()

    async def main():

        snapshotting_task = None

        while True:
            key, value = await ar.brpop(f'hq_assist_{assist_idx}')
            msg = json.loads(value)
            print(
                f'{datetime.now().strftime("%H:%M:%S")}: Assist[{assist_idx}] {msg}')

            if msg['command'] == 'snapshotting':
                snapshotting_task = asyncio.create_task(
                    snapshotting(msg['date']))

            elif msg['command'] == 'compute_statistics':
                try:
                    compute_statistics(msg['date'])
                    await ar.lpush(f'hq_assist_{assist_idx}_compute_statistics', json.dumps({"status": 'success'}))
                except Exception as e:
                    error = {
                        "status": 'failed',
                        "exception": str(e),
                        'traceback': traceback.format_exc()
                    }
                    await ar.lpush(f'hq_assist_{assist_idx}_compute_statistics', json.dumps(error))

            elif msg['command'] == 'incremental_save':
                dd, scope = get_daily_data(msg['date'])
                dd.incremental_save(msg['idx'])

            elif msg['command'] == 'quit':

                if snapshotting_task and snapshotting_task.done() is False:
                    print(
                        f'Assist[{assist_idx}]: snapshotting_task is going to be canceled')
                    snapshotting_task.cancel()

                print(
                    f'Assist[{assist_idx}]: sharedmemory is going to be closed')
                for date in data:
                    data[date][0].close_sharedmemory()
                break

            else:
                pass

    asyncio.run(main())
    # asyncio.create_task(main())

    return data


async def start_snapshot_listening(date=time.strftime('%Y%m%d')):

    check_points_length = int(rd.get(f'hq_{date}_check_points_length'))
    assist_count = int(rd.get('hq_assist_count'))

    results = [None for _ in range(assist_count)]
    status = np.zeros(check_points_length, dtype=int)

    def pre_handler(message):
        assist_idx = int(str(message['channel']).split('_')[2])
        data = json.loads(message['data'])
        results[assist_idx] = data

        check_point_idx = int(data['idx'])
        status[check_point_idx] += 1

        if status[check_point_idx] == assist_count:
            for handler in snapshot_handlers:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(results[:]))
                else:
                    handler(results[:])

        # if data['status'] == 'successful':

        #     if status[check_point_idx] == assist_count:
        #         for handler in snapshot_handlers:
        #             handler(data)
        #     # print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} ss_handler:',
        #     #       assist_idx, check_point_idx, status[check_point_idx])
        # else:
        #     print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} ss_handler:',
        #           assist_idx, check_point_idx, message['data'])

    p = ar.pubsub()
    await p.psubscribe(**{'hq_assist_*_snapshotting': pre_handler})

    while status[-1] != assist_count:

        message = await p.get_message()

        # if np.sum(status) >= assist_count:
        #     break

    await asyncio.sleep(5)
    await p.punsubscribe('hq_assist_*_snapshotting')
    p.close()


def add_snapshot_handler(handler):
    if handler in snapshot_handlers:
        return

    snapshot_handlers.append(handler)


def remove_snapshot_handler(handler):

    if handler not in snapshot_handlers:
        return

    idx = snapshot_handlers.index(handler)
    if idx != -1:
        snapshot_handlers.pop(idx)


if __name__ == '__main__':
    rd = redis.Redis(host='127.0.0.1', port=6379, db=8)

    symbol_count = len(Utils.get_symbols()) + 10
    assist_count = math.ceil(symbol_count/800)+1

    rd.set('hq_assist_count', assist_count)

    processes = []
    for _ in range(assist_count):
        proc = Process(target=assist, args=(_, assist_count))
        processes.append(proc)
        proc.start()

    for proc in processes:
        proc.join()
