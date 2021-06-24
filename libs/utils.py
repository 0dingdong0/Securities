import os
import time
import json
import redis
import tushare as ts

ts.set_token('aecca28adc0d5a7764b748ccd48bef923d81314ae47b4d44d51fce67')
tsp = ts.pro_api()


class Utils:

    rd = redis.Redis(host='127.0.0.1', port=6379, db=8)
    SYMBOLS_FILE = os.path.join(os.getcwd(), "symbols.json")
    SUSPENDED_SYMBOLS_FILE = os.path.join(
        os.getcwd(), "suspended_symbols.json")

    @staticmethod
    def get_symbols():
        if not os.path.exists(Utils.SYMBOLS_FILE):
            return []

        with open(Utils.SYMBOLS_FILE) as f:
            return json.load(f)

    @staticmethod
    def get_suspended_symbols():
        if not os.path.exists(Utils.SUSPENDED_SYMBOLS_FILE):
            return []

        with open(Utils.SUSPENDED_SYMBOLS_FILE) as f:
            return json.load(f)

    @staticmethod
    def get_running_symbols():
        return list([symbol for symbol in Utils.get_symbols() if symbol not in Utils.get_suspended_symbols()])

    @staticmethod
    def update_symbols():
        df = tsp.stock_basic(
            fields='symbol,name,market,area,industry,list_date')
        df = df.loc[df['list_date'] <= time.strftime(
            '%Y%m%d', time.localtime())]
        symbols = df['symbol'].to_list()
        with open(Utils.SYMBOLS_FILE, "w") as f:
            f.write(json.dumps(symbols))

        today = time.strftime('%Y%m%d')
        suspended_symbols = list([x[:6] for x in tsp.suspend_d(
            suspend_type='S', trade_date=today)['ts_code'].to_list()])
        with open(Utils.SUSPENDED_SYMBOLS_FILE, "w") as f:
            f.write(json.dumps(suspended_symbols))

    @staticmethod
    def is_closed_day(day=None):
        if day is None:
            day = time.strftime('%Y%m%d')

        key = day+'_is_closed_day'

        if Utils.rd.get(key):
            return False if Utils.rd.get(key) == b'false' else True

        df = tsp.trade_cal(exchange='SSE', start_date=day, end_date=day)
        if df.iloc[0]['is_open'] == 1:
            Utils.rd.set(key, 'false')
            return False
        else:
            Utils.rd.set(key, 'true')
            return True

    @staticmethod
    def get_pretrade_date(day=None):
        if day is None:
            day = time.strftime('%Y%m%d')
        df = tsp.trade_cal(exchange='SSE', start_date=day, end_date=day,
                           fields="exchange,cal_date,is_open,pretrade_date")
        return df.at[0, 'pretrade_date']

    @staticmethod
    def get_last_trade_date():
        day = time.strftime('%Y%m%d')
        df = tsp.trade_cal(exchange='SSE', start_date=day, end_date=day,
                           fields="exchange,cal_date,is_open,pretrade_date")
        if df.iloc[0]['is_open'] == 1:
            return day
        else:
            return df.at[0, 'pretrade_date']

    @staticmethod
    def get_check_points(interval=5):

        test_check_points = Utils.rd.get('test_check_points')
        if test_check_points:
            return json.loads(test_check_points)

        trading_times = [
            '09:14:50',
            ['09:15:00', '09:25:00'],
            '09:25:15',
            ['09:30:00', '11:30:00'],
            '11:30:10',
            ['13:00:00', '15:00:00'],
            '15:00:10'
        ]

        check_points = []
        today = time.strftime('%Y-%m-%d')
        for time_range in trading_times:
            if type(time_range) == list:
                start = int(time.mktime(time.strptime(
                    f'{today} {time_range[0]}', '%Y-%m-%d %H:%M:%S')))
                end = int(time.mktime(time.strptime(
                    f'{today} {time_range[1]}', '%Y-%m-%d %H:%M:%S')))
                check_points.append(
                    list([_ for _ in range(start, end+interval, interval)]))
            else:
                check_points.append(
                    [int(time.mktime(time.strptime(f'{today} {time_range}', '%Y-%m-%d %H:%M:%S')))])

        return sum(check_points, [])
