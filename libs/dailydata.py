import os
import h5py
import time
import math
import redis
import ctypes
import numpy as np
import pandas as pd
# from multiprocessing.sharedctypes import RawArray
from multiprocessing.shared_memory import SharedMemory
from libs.quotation import Quotation
from libs.tdx import TDX


class DailyData:

    rd = redis.Redis(host='127.0.0.1', port=6379, db=8)

    basics_columns = ['zt_price', 'dt_price', 'ma5vpm',
                      'mcap', 'sum4', 'sum9', 'sum19', 'sum29', 'sum59']
    snapshots_columns = ['open', 'close', 'now', 'high',
                         'low', 'turnover', 'volume', 'bid1', 'bid1_volume']
    statistic_columns = ['zhangfu', 'junjia', 'liangbi', 'zhangsu',
                         'tingban', 'sum5', 'sum10', 'sum20', 'sum30', 'sum60']

    # date: %Y%m%d
    def __init__(self, date=None, symbols=[], check_points=[], create=False):

        if date is None:
            self.date = time.strftime('%Y%m%d')
        else:
            self.date = date

        self.hdf5_file = os.path.join(
            os.getcwd(), 'storage', f'{self.date}.hdf5')

        if create:
            self.rd.set(f'hq_{self.date}_symbols_length', len(symbols))
            self.rd.set(f'hq_{self.date}_check_points_length',
                        len(check_points))

            self.shm_symbols = SharedMemory(
                name=f'${self.date}_symbols', create=True, size=len(symbols)*np.dtype('<U6').itemsize)
            self.shm_names = SharedMemory(name=f'${self.date}_names', create=True, size=len(
                symbols)*np.dtype('<U4').itemsize)
            self.shm_check_points = SharedMemory(
                name=f'${self.date}_check_points', create=True, size=len(check_points)*np.dtype('<u4').itemsize)
            self.shm_basics = SharedMemory(name=f'${self.date}_basics', create=True, size=len(
                check_points)*len(symbols)*len(self.basics_columns)*np.dtype('<f8').itemsize)
            self.shm_snapshots = SharedMemory(name=f'${self.date}_snapshots', create=True, size=len(
                check_points)*len(symbols)*len(self.snapshots_columns)*np.dtype('<f8').itemsize)
            self.shm_statistic = SharedMemory(name=f'${self.date}_statistic', create=True, size=len(
                check_points)*len(symbols)*len(self.statistic_columns)*np.dtype('<f8').itemsize)

            self.symbols = np.ndarray(
                (len(symbols),), dtype='<U6', buffer=self.shm_symbols.buf)
            self.names = np.ndarray(
                (len(symbols),), dtype='<U4', buffer=self.shm_names.buf)
            self.check_points = np.ndarray(
                (len(check_points),),
                dtype='<u4',
                buffer=self.shm_check_points.buf
            )

        else:
            self.shm_symbols = SharedMemory(name=f'${self.date}_symbols')
            self.shm_names = SharedMemory(name=f'${self.date}_names')
            self.shm_check_points = SharedMemory(
                name=f'${self.date}_check_points')
            self.shm_basics = SharedMemory(name=f'${self.date}_basics')
            self.shm_snapshots = SharedMemory(name=f'${self.date}_snapshots')
            self.shm_statistic = SharedMemory(name=f'${self.date}_statistic')

            symbols_length = int(self.rd.get(f'hq_{self.date}_symbols_length'))
            check_points_length = int(self.rd.get(
                f'hq_{self.date}_check_points_length'))

            self.symbols = np.ndarray(
                (symbols_length,), dtype='<U6', buffer=self.shm_symbols.buf)
            self.names = np.ndarray(
                (symbols_length,), dtype='<U4', buffer=self.shm_names.buf)
            self.check_points = np.ndarray(
                (check_points_length,),
                dtype='<u4',
                buffer=self.shm_check_points.buf
            )

            self.post_init()

        self.basics = np.ndarray(
            (len(self.symbols), len(self.basics_columns)),
            dtype='<f8',
            buffer=self.shm_basics.buf
        )
        self.snapshots = np.ndarray(
            (len(self.check_points), len(self.symbols), len(self.snapshots_columns)),
            dtype='<f8',
            buffer=self.shm_snapshots.buf
        )
        self.statistic = np.ndarray(
            (len(self.check_points), len(self.symbols), len(self.statistic_columns)),
            dtype='<f8',
            buffer=self.shm_statistic.buf
        )

    async def prepare(self, symbols, check_points):
        q = Quotation(symbols)
        snapshot = await q.snapshot()

        self.symbols[:] = symbols[:]
        self.names[:] = [snapshot[symbol]['name'] for symbol in symbols][:]
        self.check_points[:] = check_points[:]

        self.basics.fill(np.nan)
        self.snapshots.fill(np.nan)
        self.statistic.fill(np.nan)

        market_values = await q.get_market_values()

        await q.exit()

        tdx = TDX()
        # assert tdx.is_local_tdx_data_outdated() is not True
        klines = tdx.kline(symbols)

        for _, symbol in enumerate(symbols):
            self.basics[_, 0] = market_values[symbol]['zt_price']
            self.basics[_, 1] = market_values[symbol]['dt_price']
            self.basics[_, 3] = market_values[symbol]['mcap']

            if symbol not in klines:
                continue

            kline = klines[symbol]
            self.basics[_, 2] = kline.iloc[0 -
                                           min(5, len(kline)):]['volume'].sum()/1200
            self.basics[_, 4] = kline.iloc[-4:]['close'].sum() if len(kline) >= 4 else np.nan
            self.basics[_, 5] = kline.iloc[-9:]['close'].sum() if len(kline) >= 9 else np.nan
            self.basics[_, 6] = kline.iloc[-19:]['close'].sum() if len(kline) >= 19 else np.nan
            self.basics[_, 7] = kline.iloc[-29:]['close'].sum() if len(kline) >= 29 else np.nan
            self.basics[_, 8] = kline.iloc[-59:]['close'].sum() if len(kline) >= 59 else np.nan

        # await q.exit()
        self.post_init()

    def post_init(self):
        self.active_time_blocks = []
        self.check_interval = self.check_points[2] - self.check_points[1]
        start_time_0_str = f'{time.strftime("%Y-%m-%d", time.localtime(self.check_points[0]))} 09:15:00'
        start_time_1_str = f'{time.strftime("%Y-%m-%d", time.localtime(self.check_points[0]))} 09:30:00'
        start_time_2_str = f'{time.strftime("%Y-%m-%d", time.localtime(self.check_points[0]))} 13:00:00'
        end_time_0_str = f'{time.strftime("%Y-%m-%d", time.localtime(self.check_points[0]))} 09:25:00'
        end_time_1_str = f'{time.strftime("%Y-%m-%d", time.localtime(self.check_points[0]))} 11:30:00'
        end_time_2_str = f'{time.strftime("%Y-%m-%d", time.localtime(self.check_points[0]))} 15:00:00'
        start_time_0 = int(time.mktime(time.strptime(
            start_time_0_str, '%Y-%m-%d %H:%M:%S')))
        start_time_1 = int(time.mktime(time.strptime(
            start_time_1_str, '%Y-%m-%d %H:%M:%S')))
        start_time_2 = int(time.mktime(time.strptime(
            start_time_2_str, '%Y-%m-%d %H:%M:%S')))
        end_time_0 = int(time.mktime(time.strptime(
            end_time_0_str, '%Y-%m-%d %H:%M:%S')))
        end_time_1 = int(time.mktime(time.strptime(
            end_time_1_str, '%Y-%m-%d %H:%M:%S')))
        end_time_2 = int(time.mktime(time.strptime(
            end_time_2_str, '%Y-%m-%d %H:%M:%S')))

        if start_time_0 >= self.check_points[0]:
            start_time_idx_0 = np.where(
                self.check_points == start_time_0)[0][0]
            end_time_idx_0 = np.where(self.check_points == end_time_0)[0][0]

            self.active_time_blocks.append(
                (
                    (start_time_idx_0, start_time_0, start_time_0_str),
                    (end_time_idx_0, end_time_0, end_time_0_str)
                )
            )

        start_time_idx_1 = np.where(self.check_points == start_time_1)[0][0]
        end_time_idx_1 = np.where(self.check_points == end_time_1)[0][0]
        self.active_time_blocks.append(
            (
                (start_time_idx_1, start_time_1, start_time_1_str),
                (end_time_idx_1, end_time_1, end_time_1_str)
            )
        )
        start_time_idx_2 = np.where(self.check_points == start_time_2)[0][0]
        end_time_idx_2 = np.where(self.check_points == end_time_2)[0][0]
        self.active_time_blocks.append(
            (
                (start_time_idx_2, start_time_2, start_time_2_str),
                (end_time_idx_2, end_time_2, end_time_2_str)
            )
        )
        # self.rd.set(f'{self.date}_data_ready', 'true')

    def get_securities(self):
        return pd.DataFrame({
            "symbol": self.symbols,
            "name": self.names,
            "zt_price": self.basics[:, 0],
            "dt_price": self.basics[:, 1],
            "ma5vpm": self.basics[:, 2],
            "mcap": self.basics[:, 3],
            "sum4": self.basics[:, 4],
            "sum9": self.basics[:, 5],
            "sum19": self.basics[:, 6],
            "sum29": self.basics[:, 7],
            "sum59": self.basics[:, 8]
        }).set_index('symbol')

    # check_point: timestamp or %H:%M:%S

    def get_snapshot(self, check_point):
        if type(check_point) == int and check_point <= 100000:
            index = check_point
        elif type(check_point) == float or type(check_point) == int:
            index = np.where(self.check_points == check_point)[0][0]
        elif type(check_point) == str:
            index = [time.strftime('%H:%M:%S', time.localtime(cp))
                     for cp in self.check_points].index(check_point)

        return pd.DataFrame({
            "datetime": [check_point if type(check_point) == str else time.strftime('%H:%M:%S', time.localtime(check_point)) for _ in range(len(self.symbols))],
            "timestamp": [self.check_points[index] if type(check_point) == str else check_point for _ in range(len(self.symbols))],
            "symbol": self.symbols,
            "name": self.names,
            "open": self.snapshots[index, :, 0],
            "close": self.snapshots[index, :, 1],
            "now": self.snapshots[index, :, 2],
            "high": self.snapshots[index, :, 3],
            "low": self.snapshots[index, :, 4],
            "turnover": self.snapshots[index, :, 5],
            "volume": self.snapshots[index, :, 6],
            "bid1": self.snapshots[index, :, 7],
            "bid1_volume": self.snapshots[index, :, 8],
            "zhangfu": self.statistic[index, :, 0],
            "junjia": self.statistic[index, :, 1],
            "liangbi": self.statistic[index, :, 2],
            "zhangsu": self.statistic[index, :, 3],
            "tingban": self.statistic[index, :, 4],
            "ma5": self.statistic[index, :, 5]
        }).set_index('symbol')

    # dt: %Y%m%d
    def save(self, gzip_level=4):
        folder = os.path.join(os.getcwd(), 'storage')
        if not os.path.exists(folder):
            os.mkdir(folder)
#         file = os.path.join(folder, f'{self.date}.hdf5')

        if os.path.exists(self.hdf5_file):
            print('?????? [', self.hdf5_file, '] ??????????????????????????? ... ... ', end='')
            os.remove(self.hdf5_file)
            print('????????????')

        symbols = np.char.encode(self.symbols, encoding='utf-8')
        names = np.char.encode(self.names, encoding='utf-8')
        with h5py.File(self.hdf5_file, "a") as f:
            f.create_dataset(u"symbols", data=symbols,
                             compression="gzip", compression_opts=gzip_level)
            f.create_dataset(u"names", data=names,
                             compression="gzip", compression_opts=gzip_level)
            f.create_dataset(u"check_points", data=self.check_points,
                             compression="gzip", compression_opts=gzip_level)
            f.create_dataset(u"basics", data=self.basics,
                             compression="gzip", compression_opts=gzip_level)
            f.create_dataset(u"snapshots", data=self.snapshots,
                             compression="gzip", compression_opts=gzip_level)
#             f.create_dataset(u"statistic", data=self.statistic, compression="gzip", compression_opts=gzip_level)

        print('?????? ?????? ???????????????', self.hdf5_file)

    # dt: %Y%m%d
    @staticmethod
    def load(dt=None):
        date = time.strftime("%Y%m%d", time.localtime()) if dt is None else dt
        file = os.path.join(os.getcwd(), 'storage', f'{date}.hdf5')
        assert os.path.exists(file), 'file['+file+'] does not exists!'

        with h5py.File(file, "a") as f:
            symbols = np.char.decode(f[u'symbols'], 'utf-8')
            check_points = f[u'check_points'][:]

            data = DailyData(date=date, symbols=symbols,
                             check_points=check_points, create=True)
            data.symbols[:] = symbols[:]
            data.names[:] = np.char.decode(f[u'names'], 'utf-8')
            data.check_points[:] = check_points
            data.basics[:, :] = f[u'basics'][:, :]
            data.snapshots[:, :, :] = f[u'snapshots'][:, :, :]
#             data.statistic[:,:,:] = f[u'statistic'][:,:,:]

        data.post_init()
        return data

    def get_ma5pm_anchor_idx(self, idx):

        if self.check_interval == 60:
            if idx <= 121:
                return max(0, idx-5)
            elif idx <= 126:
                return idx-6
            else:
                return idx-5
        else:
            # st = time.time()

            ck = self.check_points[idx]

            if ck <= self.active_time_blocks[0][0][1]+300:
                ma5pm_anchor_idx = self.active_time_blocks[0][0][0] - 1

            elif self.active_time_blocks[0][1][1] < ck < self.active_time_blocks[1][0][1]:
                ma5pm_anchor_idx = int(
                    self.active_time_blocks[0][1][0] - 300/self.check_interval)

            elif self.active_time_blocks[1][0][1] <= ck <= self.active_time_blocks[1][0][1]+300:
                ma5pm_anchor_idx = self.active_time_blocks[1][0][0] - 1

            elif self.active_time_blocks[1][1][1] < ck < self.active_time_blocks[2][0][1]:
                ma5pm_anchor_idx = int(
                    self.active_time_blocks[1][1][0] - 300/self.check_interval)

            elif self.active_time_blocks[2][0][1] <= ck <= self.active_time_blocks[2][0][1]+300:
                result = math.ceil(self.check_points[idx]/60)*60-300
                offset = int(
                    (result-self.check_points[idx])/self.check_interval)

                ma5pm_anchor_idx = int(
                    max(idx+offset-2, self.active_time_blocks[1][1][0] - 240/self.check_interval))

                if ma5pm_anchor_idx == self.active_time_blocks[1][1][0]:
                    ma5pm_anchor_idx += 1

            elif self.active_time_blocks[2][1][1] < ck:
                ma5pm_anchor_idx = int(
                    self.active_time_blocks[2][1][0]-300/self.check_interval)

            else:
                result = math.ceil(self.check_points[idx]/60)*60-300
                offset = int(
                    (result-self.check_points[idx])/self.check_interval)

                ma5pm_anchor_idx = idx+offset

            # et = time.time()

            # print(
            #     idx, ' : ', ma5pm_anchor_idx, '       ',
            #     time.strftime("%H:%M:%S", time.localtime(self.check_points[idx])),
            #     ' ==> ',
            #     time.strftime("%H:%M:%S", time.localtime(self.check_points[ma5pm_anchor_idx])), '       ',
            #     ck, ' : ', self.check_points[ma5pm_anchor_idx], '       ',
            #     et-st
            # )

            return ma5pm_anchor_idx

    def get_time_lapse(self, idx):

        ck = self.check_points[idx]
        diff_0000 = (ck+28800) % 86400  # 8*3600=28800, 24*3600=86400

        if diff_0000 <= 33300:  # 09:15:00, 9*3600+15*60=33300
            return 1
        elif diff_0000 <= 33900:  # 09:25:00, 9*3600+25*60=33900
            return math.ceil((diff_0000-33300)/60)
        elif diff_0000 < 34200:  # 09:30:00, 9*3600+30*60=34200
            return 10
        elif diff_0000 <= 41400:  # 11:30:00, 11*3600+30*60=41400
            return max(1, math.ceil((diff_0000-34200)/60))
        elif diff_0000 < 46800:  # 13:00:00, 13*3600=46800
            return 120
        elif diff_0000 <= 54000:  # 15:00:00, 15*3600=54000
            return 120+max(1, math.ceil((diff_0000-46800)/60))
        else:
            return 240

    def close_sharedmemory(self):
        self.shm_symbols.close()
        self.shm_names.close()
        self.shm_check_points.close()
        self.shm_basics.close()
        self.shm_snapshots.close()
        self.shm_statistic.close()

    def unlink_sharedmemory(self):
        self.shm_symbols.unlink()
        self.shm_names.unlink()
        self.shm_check_points.unlink()
        self.shm_basics.unlink()
        self.shm_snapshots.unlink()
        self.shm_statistic.unlink()

    def incremental_save(self, idx):
        # with h5py.File(self.hdf5_file, "r+") as f:
        #     f[u'snapshots'][idx] = self.snapshots[idx]

        if not hasattr(self, 'hdf5'):
            if not os.path.exists(self.hdf5_file):
                return 'file['+self.hdf5_file+'] does not exists!'
            self.hdf5 = h5py.File(self.hdf5_file, 'r+')

        self.hdf5[u'snapshots'][idx] = self.snapshots[idx]

        if (idx+1) == len(self.check_points):
            self.hdf5.close()
        else:
            self.hdf5.flush()
