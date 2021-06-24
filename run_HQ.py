import time
import math
import json
import redis
import asyncio
import numpy as np
from aredis import StrictRedis
from multiprocessing import Process

from libs.tdx import TDX
from libs.utils import Utils
from libs.assist import assist
from libs.dailydata import DailyData

policy = asyncio.WindowsSelectorEventLoopPolicy()
asyncio.set_event_loop_policy(policy)

date = time.strftime('%Y%m%d')
rd = redis.Redis(host='127.0.0.1', port=6379, db=8)
ar = StrictRedis(host='127.0.0.1', port=6379, db=8)

for key in rd.keys():
    if key.decode("utf-8") .startswith('test'):
        continue
    rd.delete(key)

# for key in rd.keys():
#     print(key)


async def save(data):

    now = time.time()
    save_time = int(
        time.mktime(time.strptime(f'{date} 15:00:30', '%Y-%m-%d %H:%M:%S')))

    # save_time = data.check_points[-1]+10

    if save_time > now:
        await asyncio.sleep(save_time-now)
        data.save()


async def start_snapshotting(assist_count):

    # await asyncio.sleep(int(time.mktime(time.strptime(f'{date} 09:14:00', '%Y-%m-%d %H:%M:%S'))) - time.time())

    # while await ar.get('hq_assist_count') is None:
    #     await asyncio.sleep(1)

    # assist_count = int(rd.get('hq_assist_count'))

    await asyncio.sleep(3)
    msg = {
        'command': 'snapshotting',
        'date': time.strftime('%Y%m%d')
    }

    for _ in range(assist_count):
        rd.lpush(f'hq_assist_{_}', json.dumps(msg))


async def incremental_save(assist_count, check_points_length):

    # await asyncio.sleep(int(time.mktime(time.strptime(f'{time.strftime("%Y-%m-%d")} 09:14:30', '%Y-%m-%d %H:%M:%S'))) - time.time())

    # check_points_length = int(rd.get(f'hq_{date}_check_points_length'))
    # assist_count = int(rd.get('hq_assist_count'))

    subs = [ar.pubsub() for assist_idx in range(assist_count)]

    results = await asyncio.gather(*[sub.subscribe(f'hq_assist_{_}_snapshotting') for _, sub in enumerate(subs)])
    results = await asyncio.gather(*[sub.parse_response() for sub in subs])

    # assert all([result[0] == b'subscribe' and result[-1]
    #            == 1 for result in results])

    while True:
        results = await asyncio.gather(*[sub.parse_response() for sub in subs])
        results = [json.loads(result[2]) for result in results]

        if not all(
            result['status'] == 'successful' and result['idx'] == results[0]['idx'] for result in results
        ):
            print('|||||||||||Error: Message in subscription has different check_points!')
            continue

        idx = results[0]['idx']
        msg = {
            'command': 'incremental_save',
            'date': date,
            'idx': idx
        }
        rd.lpush(f'hq_assist_0', json.dumps(msg))

        if idx+1 == check_points_length:
            break

    results = await asyncio.gather(*[sub.unsubscribe(f'hq_assist_{_}_snapshotting') for _, sub in enumerate(subs)])
    results = await asyncio.gather(*[sub.parse_response() for sub in subs])
    # assert all([result[0] == b'unsubscribe' and result[-1]
    #            == 0 for result in results])


async def main(symbols, check_points, assist_count):

    data = DailyData(date=date, symbols=symbols,
                     check_points=check_points, create=True)

    await data.prepare(symbols, check_points)
    # task_prepare = asyncio.create_task(data.prepare(symbols, check_points))
    # while not task_prepare.done():
    #     print('wait data prepare', task_prepare)
    #     time.sleep(1)
    data.save()

    await asyncio.gather(*[incremental_save(assist_count, len(check_points)), start_snapshotting(assist_count), save(data)])


if __name__ == '__main__':

    if not Utils.is_closed_day():
        now = time.time()
        initial_time = int(
            time.mktime(time.strptime(f'{date} 09:10:30', '%Y-%m-%d %H:%M:%S'))
        )
        # check_points = Utils.get_check_points(interval=5)
        # initial_time = check_points[0]-135
        # print(check_points, initial_time-now)

        if initial_time > now:
            time.sleep(initial_time-now)

        Utils.update_symbols()
        symbols = Utils.get_running_symbols()
        check_points = Utils.get_check_points(interval=5)
        assist_count = math.ceil(len(symbols)/800)+1

        rd.set(f'hq_assist_count', assist_count)

        processes = []
        for _ in range(assist_count):
            proc = Process(target=assist, args=(_, assist_count))
            processes.append(proc)
            proc.start()

        asyncio.run(main(symbols, check_points, assist_count))

        for proc in processes:
            proc.join()
