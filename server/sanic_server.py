import os
import sys
import time
import uuid
import asyncio
from sanic import Sanic
from pathlib import Path
from datetime import datetime
from sanic.models.handler_types import RequestMiddlewareType
from sanic.response import text
from sanic.response import json

from libs.assist import start_snapshot_listening
from libs.assist import add_snapshot_handler

# currentdir = os.path.dirname(os.path.realpath(__file__))
# parentdir = os.path.dirname(currentdir)
# sys.path.append(parentdir)

app = Sanic("My Hello, world app")


app.static("/favicon.ico", "server/static/favicon.png")
app.static("/static", "server/static/")

# todo: setup app.ctx.data = {}, date => dailydata
app.ctx.queues = []


async def snapshot_handler(results):
    if all([result['status'] == 'successful'] and result['idx'] == results[0]['idx'] for result in results):
        # todo: notify updates
        pass
    else:
        print(f'\n{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}====================== abnormal snapchoting results ======================')
        for result in results:
            print(result)


@app.on_request
async def identify_user_id(request):
    if "user_id" in request.cookies:
        request.ctx.user_id = request.cookies.get('user_id')
    else:
        request.ctx.user_id = str(uuid.uuid4())


@app.on_response
async def set_user_id(request, response):
    if "user_id" not in response.cookies:
        response.cookies['user_id'] = request.ctx.user_id


@app.get("/market/<date>")
async def market(request, date):
    ts = request.args.get("ts")
    if ts is None:
        ts = time.time()
    return text(f'daily_data(): {date}, {ts}, {request.id}')


@app.get("/kline/<symbol>")
async def kline(request, symbol):
    start_date = request.args.get("start")
    end_date = request.args.get("end")
    return text(f'Hello, world! {start_date} {end_date}')


@app.get("/fenshi/<symbol>")
async def fenshi(request, symbol):
    date = request.args.get("ts")
    if date is None:
        date = time.strftime('%Y%m%d')

    ts = request.args.get("ts")
    if ts is None:
        ts = time.time()
    return text(f'Hello, world! {date} {ts}')


@app.websocket("/websocket/<room>")
async def websocket(request, ws, room):
    # todo: create queue and add to app.ctx.queues
    queue = asyncio.Queue()
    app.ctx.queue.append(queue)

    msg = "hello"
    while True:
        # todo: wait for any : ws.recv(), queue.get()
        await ws.send(msg)
        msg = await ws.recv()

    # todo: remove queue from app.ctx.queues when ws closed


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1234, debug=True)
