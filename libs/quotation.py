import os
import re
import time
import math
import json
import random
import asyncio
import aiohttp
import numpy as np
import pandas as pd
from libs.utils import Utils

np.set_printoptions(formatter={'float': lambda x: "{0:0.2f}".format(x)})
pd.options.display.float_format = '{:,.2f}'.format

policy = asyncio.WindowsSelectorEventLoopPolicy()
asyncio.set_event_loop_policy(policy)

HEADERS = [
    ('User-Agent', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36'),
    ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'),
    ('Accept-Encoding', 'gzip, deflate'),
    ('Accept-Language', 'zh-CN,zh;q=0.8,en-US;q=0.6,en;q=0.5;q=0.4')
]


async def get(session, url, ssl=False):
    async with session.get(url, ssl=ssl) as resp:
        assert resp.status == 200
        return await resp.text()


class Quotation:

    api = 'http://hq.sinajs.cn/list='
    max_group_size = 800
    symbols = []

    def __init__(self, symbols=None, group_count=1):
        if symbols:
            self.symbols = symbols
        else:
            self.symbols = Utils.get_running_symbols()

        min_group_count = math.ceil(len(self.symbols)/self.max_group_size)
        if group_count < min_group_count:
            self.group_count = min_group_count
        else:
            self.group_count = group_count
        self.group_size = math.ceil(len(self.symbols)/self.group_count)

        symbols_with_prefix = list(
            map(lambda x: 'sh'+x[-6:] if x[0] == '6' else 'sz'+x[-6:], self.symbols))
        self.symbol_groups = list([
            ','.join(
                symbols_with_prefix[idx*self.group_size:min(
                    (idx+1)*self.group_size, len(self.symbols))]
            ) for idx in range(self.group_count)
        ])

        timeout = aiohttp.ClientTimeout(total=2)
        self.sessions = [aiohttp.ClientSession(
            headers=HEADERS, timeout=timeout) for _ in range(self.group_count)]

    def parse_real_data(self, data_str, array=None):

        grep_str = re.compile(
            r'(\d+)="([^,=]+)%s%s'
            % (r",([\.\d]+)" * 29, r",([-\.\d:]+)" * 2)
        )

        results = grep_str.finditer(data_str)

        if array is not None:
            idx = -1
            for stock_match_object in results:
                idx += 1
                stock = stock_match_object.groups()

                array[idx, 0] = float(stock[2])   # open
                array[idx, 1] = float(stock[3])   # close
                array[idx, 2] = float(stock[4])   # now
                array[idx, 3] = float(stock[5])   # high
                array[idx, 4] = float(stock[6])   # low
                array[idx, 5] = float(stock[9])   # turnover
                if array[idx, 5] == 0 and stock[4] != stock[7] and stock[7] == stock[8]:
                    array[idx, 2] = float(stock[7])
                    array[idx, 5] = float(stock[11])
                array[idx, 6] = float(stock[10])   # volume
                array[idx, 7] = float(stock[12])   # bid1
                array[idx, 8] = float(stock[11])   # bid1_volume

        else:
            stock_dict = dict()
            for stock_match_object in results:
                stock = stock_match_object.groups()
                stock_dict[stock[0]] = dict(
                    name=stock[1],
                    open=float(stock[2]),
                    close=float(stock[3]),
                    now=float(stock[4]),
                    high=float(stock[5]),
                    low=float(stock[6]),
                    buy=float(stock[7]),
                    sell=float(stock[8]),
                    turnover=int(stock[9]),
                    volume=float(stock[10]),
                    bid1_volume=int(stock[11]),
                    bid1=float(stock[12]),
                    bid2_volume=int(stock[13]),
                    bid2=float(stock[14]),
                    bid3_volume=int(stock[15]),
                    bid3=float(stock[16]),
                    bid4_volume=int(stock[17]),
                    bid4=float(stock[18]),
                    bid5_volume=int(stock[19]),
                    bid5=float(stock[20]),
                    ask1_volume=int(stock[21]),
                    ask1=float(stock[22]),
                    ask2_volume=int(stock[23]),
                    ask2=float(stock[24]),
                    ask3_volume=int(stock[25]),
                    ask3=float(stock[26]),
                    ask4_volume=int(stock[27]),
                    ask4=float(stock[28]),
                    ask5_volume=int(stock[29]),
                    ask5=float(stock[30]),
                    date=stock[31],
                    time=stock[32],
                )

            return stock_dict

    async def exit(self):
        for session in self.sessions:
            await session.close()

    async def snapshot(self, array=None):
        urls = [f'{self.api}{symbols}' for symbols in self.symbol_groups]
        results = await asyncio.gather(*[get(self.sessions[_], urls[_]) for _ in range(self.group_count)])
        return self.parse_real_data(''.join(results), array=array)

    async def get_market_values(self):

        urls = [
            f'http://sqt.gtimg.cn/utf8/offset=1,2,3,45,46,31,48,49&q={symbols}' for symbols in self.symbol_groups]
        results = await asyncio.gather(*[get(self.sessions[_], urls[_]) for _ in range(self.group_count)])
        # grep_str = re.compile(r'\d+="(\d+)~([^~]+)~(\d+)~([.\d]+)~([.\d]+)~(\d+)~([-.\d]+)~([-.\d]+)";\n')
        grep_str = re.compile(
            r'\d+="(\d+)~([^~]+)~(\d*)~([.\d]*)~([.\d]*)~(\d+)~([-.\d]+)~([-.\d]+)";\n')
        results = grep_str.finditer(''.join(results))
        stock_dict = dict()
        for stock_match_object in results:
            stock = stock_match_object.groups()
            stock_dict[stock[2]] = dict(
                name=stock[1],
                symbol=stock[2],
                # mcap=float(stock[3]),
                # tcap=float(stock[4]),
                mcap=float(stock[3]) if stock[3] else np.nan,
                tcap=float(stock[4]) if stock[4] else np.nan,
                zt_price=np.nan if stock[6].startswith(
                    '-') else float(stock[6]),
                dt_price=np.nan if stock[6].startswith(
                    '-') else float(stock[7]),
                dt=stock[5],
            )
        return stock_dict

    async def real(self, symbols):
        length = len(symbols)
        symbols_with_prefix = list(
            map(lambda x: 'sh'+x[-6:] if x[0] == '6' else 'sz'+x[-6:], symbols))
        group_count = math.ceil(length/self.max_group_size)
        group_size = math.ceil(length/group_count)
        symbol_groups = list([
            ','.join(
                symbols_with_prefix[idx *
                                    group_size:min((idx+1)*group_size, length)]
            ) for idx in range(group_count)
        ])
        urls = [f'{self.api}{item}' for item in symbol_groups]
        results = await asyncio.gather(*[get(self.sessions[_], urls[_]) for _ in range(group_count)])
        return self.parse_real_data(''.join(results))

    async def kline(self, symbols, scale=240, ma=5, length=1023):
        args = (scale, ma, length)
        url = 'http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={}&scale={}&ma={}&datalen={}'
        urls = list(map(
            lambda x: url.format('sh'+x[-6:], *args) if x[0] == '6' else
            url.format('sz'+x[-6:], *args),
            symbols
        ))

        sessions = [aiohttp.ClientSession(headers=HEADERS)
                    for _ in range(len(urls))]
        results = await asyncio.gather(*[get(sessions[_], urls[_]) for _ in range(len(urls))])
        for session in sessions:
            await session.close()

        klines = list(map(
            lambda x: json.loads(
                re.sub('(\w+)\s?:\s?("?[^",]+"?,?)', "\"\g<1>\":\g<2>", x)),
            results
        ))

        securities = {}
        for idx, symbol in enumerate(symbols):
            securities[symbol] = klines[idx]

        return securities

    async def min_data(self, symbols):
        url = 'https://data.gtimg.cn/flashdata/hushen/minute/{}.js'
        urls = list(map(

            lambda x: url.format('sh'+x[-6:]) if x[0] == '6' else
            url.format('sz'+x[-6:]),
            symbols
        ))

        sessions = [aiohttp.ClientSession(headers=HEADERS)
                    for _ in range(len(urls))]
        results = await asyncio.gather(*[get(sessions[_], urls[_]) for _ in range(len(urls))])
        for session in sessions:
            await session.close()

        mdata = {}

        for _, result in enumerate(results):

            date = re.search('date:(\d+)', result).group(1)
            grep_str = re.compile(r'(\d+) ([\d.]+) (\d+)\\n')
            grep_results = grep_str.finditer(result)

            data = []
            for match_object in grep_results:
                item = match_object.groups()
                data.append((item[0], float(item[1]), int(item[2])))

            mdata[symbols[_]] = {
                'date': date,
                'data': data
            }
        return mdata
