import time
import math
import json
import redis
import shutil
import asyncio
from datetime import datetime
from aredis import StrictRedis

from libs.utils import Utils
from libs.assist import start_snapshot_listening
from libs.assist import add_snapshot_handler
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
    print('启动协程：save dailydata ....')
    now = time.time()
    save_time = int(
        time.mktime(time.strptime(f'{date} 15:00:30', '%Y%m%d %H:%M:%S')))

    if save_time > now:
        await asyncio.sleep(save_time-now)
        data.save()

        src = "D:\\workspace\\python\\Securities\\storage\\20210625.hdf5"
        dst = "D:\网盘\OneDrive_odingdongo\OneDrive\share"
        shutil.copy2(src, dst)


async def start_snapshotting(assist_count):
    print('启动协程：start_snapshotting ...')

    await asyncio.sleep(3)
    msg = {
        'command': 'snapshotting',
        'date': time.strftime('%Y%m%d')
    }

    for _ in range(assist_count):
        rd.lpush(f'hq_assist_{_}', json.dumps(msg))


def ss_handler_inc_save(results):
    if all([result['status'] == 'successful'] and result['idx'] == results[0]['idx'] for result in results):
        msg = {
            'command': 'incremental_save',
            'date': date,
            'idx': int(results[0]['idx'])
        }
        rd.lpush('hq_assist_0', json.dumps(msg))
    else:
        print(f'\n{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}====================== abnormal snapchoting results ======================')
        for result in results:
            print(result)


async def main(symbols, check_points, assist_count):

    print('初始化 DailyData ...')
    data = DailyData(date=date, symbols=symbols,
                     check_points=check_points, create=True)

    await data.prepare(symbols, check_points)
    data.save()

    add_snapshot_handler(ss_handler_inc_save)
    await asyncio.gather(*[start_snapshot_listening(), start_snapshotting(assist_count), save(data)])


if __name__ == '__main__':

    if not Utils.is_closed_day():
        now = time.time()
        initial_time = int(
            time.mktime(time.strptime(f'{date} 09:10:30', '%Y%m%d %H:%M:%S'))
        )

        if initial_time > now:
            print('wait until 09:10:30')
            time.sleep(initial_time-now)

        Utils.update_symbols()
        symbols = Utils.get_running_symbols()
        check_points = Utils.get_check_points(interval=5)
        assist_count = math.ceil(len(symbols)/800)+1

        rd.set(f'hq_assist_count', assist_count)

        asyncio.run(main(symbols, check_points, assist_count))
