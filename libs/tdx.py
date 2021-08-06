import os
import time
import struct
import numpy as np
import pandas as pd
from libs.utils import Utils

tdx_root = 'C:\\new_gjzq_v6'


class TDX:
    def __init__(self, tdx_root='C:\\new_gjzq_v6'):
        self.root = tdx_root

    def get_tdx_gainian(self):

        fname = os.path.join(self.root, 'T0002', 'hq_cache', 'block_gn.dat')
        result = {}
        if type(fname) is not bytearray:
            with open(fname, "rb") as f:
                data = f.read()
        else:
            data = fname

        pos = 384
        (num, ) = struct.unpack("<H", data[pos: pos + 2])
        pos += 2
        for i in range(num):
            blockname_raw = data[pos: pos + 9]
            pos += 9
            name = blockname_raw.decode("gbk", 'ignore').rstrip("\x00")
            stock_count, block_type = struct.unpack("<HH", data[pos: pos + 4])
            pos += 4
            block_stock_begin = pos
            codes = []
            for code_index in range(stock_count):
                one_code = data[pos: pos +
                                7].decode("utf-8", 'ignore').rstrip("\x00")
                codes.append(one_code)
                pos += 7

            gn = {}
            gn["name"] = name
            gn["block_type"] = block_type
            gn["stock_count"] = stock_count
            gn["codes"] = codes
            result[name] = gn

            pos = block_stock_begin + 2800

        return result

    def get_tdx_hangye(self):

        file_hangye = os.path.join(self.root, 'incon.dat')
        assert os.path.exists(file_hangye)
        file_stock_hangye = os.path.join(
            self.root, 'T0002', 'hq_cache', 'tdxhy.cfg')
        assert os.path.exists(file_stock_hangye), file_stock_hangye

        result = {}
        with open(file_hangye, "rt", encoding='gb2312') as f:
            isTDXHY = False
            for line in f:
                line = line.rstrip()
                if not isTDXHY and line != '#TDXNHY':
                    continue
                elif not isTDXHY and line == '#TDXNHY':
                    isTDXHY = True
                    continue
                elif isTDXHY and line == '######':
                    isTDXHY = False
                    break
                code, name = line.split('|')
                result[code] = {}
                result[code]['code'] = code
                result[code]['name'] = name
                result[code]['codes'] = []

        with open(file_stock_hangye, "rt", encoding='gb2312') as f:
            for line in f:
                line = line.rstrip()

                # print(line)
                # market_code, stock_code, tdxhy_code, swhy_code, unknown_code = line.split("|")

                parts = line.split("|")
                market_code = parts[0]
                stock_code = parts[1]
                tdxhy_code = parts[2]
                swhy_code = parts[3]

                stock_code = stock_code.strip()

                if tdxhy_code and tdxhy_code != 'T00':
                    result[tdxhy_code]['codes'].append(stock_code)
        return result

    def get_tdx_zhishu(self):

        tdxzs_cfg = os.path.join(self.root, 'T0002', 'hq_cache', 'tdxzs.cfg')
        gainian = self.get_tdx_gainian()
        hangye = self.get_tdx_hangye()

        result = {}
        with open(tdxzs_cfg, "rt", encoding='gb2312') as f:
            for line in f:
                line = line.rstrip()
                zs_name, zs_code, zs_type, num_1, num_2, key = line.split('|')

                if key in gainian:
                    if zs_code in result:
                        print(
                            '------------------------------------------------------')
                        print('in result key: ', key, zs_name, zs_code)
                        print('gainian: ', key, gainian[key])
                        continue
                    else:
                        if len(gainian[key]['codes']) == 0:
                            continue
                        zs = {}
                        zs['code'] = zs_code
                        zs['name'] = gainian[key]['name']
                        zs['codes'] = gainian[key]['codes']
                        result[zs_code] = zs

                if key in hangye:
                    if zs_code in result:
                        print(
                            '------------------------------------------------------')
                        print('in result key: ', key, zs_name, zs_code)
                        print('hangye: ', key, hangye[key])
                        continue
                    else:
                        if len(hangye[key]['codes']) == 0:
                            continue
                        zs = {}
                        zs['code'] = zs_code
                        zs['name'] = hangye[key]['name']
                        zs['codes'] = hangye[key]['codes']
                        result[zs_code] = zs

        return result

    def kline(self, symbols):
        kline = {}
        for symbol in symbols:
            market = 'sh' if symbol[0] == '6' else 'sz'
            file = f"{tdx_root}\\vipdoc\\{market}\\lday\\{market}{symbol}.day"
#             print(file)
            if not os.path.exists(file):
                print(f'{file} does not exist.')
                continue

            with open(file, 'rb') as f:
                buf = f.read()
                buf_size = len(buf)
                rec_count = int(buf_size / 32)

                data = []
                for i in range(rec_count):
                    a = struct.unpack('IIIIIfII', buf[i*32:(i+1)*32])
    #                 print(a)
                    data.append({
                        'dt': a[0],
                        'open': a[1]/100,
                        'high': a[2]/100,
                        'low': a[3]/100,
                        'close': a[4]/100,
                        'amount': a[5],
                        'volume': a[6]
                    })

            df = pd.DataFrame(data)
            df.set_index('dt', inplace=True)
            kline[symbol] = df

        return kline

    def is_local_tdx_data_outdated(self):
        today = int(time.strftime('%Y%m%d'))
        last_trade_date = int(Utils.get_last_trade_date())
        df = self.kline(['399001'])['399001']

        if df.index[-1] == last_trade_date:
            return False
        elif today != last_trade_date:
            return True
        elif time.time() > time.mktime(time.strptime(f'{today} 16:00:00', '%Y%m%d %H:%M:%S')):
            return True
        else:
            return False
