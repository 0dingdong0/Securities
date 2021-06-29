import time
import math
import redis

from datetime import datetime
from multiprocessing import Process

from libs.utils import Utils
from libs.assist import assist

if __name__ == '__main__':
    rd = redis.Redis(host='127.0.0.1', port=6379, db=8)

    for key in rd.keys():
        if key.decode("utf-8") .startswith('test'):
            continue
        rd.delete(key)

    # symbol_count = len(Utils.get_symbols()) + 10
    # assist_count = math.ceil(symbol_count/800)+1
    # rd.set('hq_assist_count', assist_count)

    while not rd.get('hq_assist_count'):
        time.sleep(1)
    assist_count = int(rd.get('hq_assist_count'))

    processes = []
    for _ in range(assist_count):
        print(
            f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} -> start assist {_}/{assist_count} ...')
        proc = Process(target=assist, args=(_, assist_count))
        processes.append(proc)
        proc.start()
        time.sleep(1)

    for proc in processes:
        proc.join()
