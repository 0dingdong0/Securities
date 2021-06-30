import time
import uuid
import asyncio
from sanic import Sanic
from datetime import datetime
from sanic.models.handler_types import RequestMiddlewareType
from sanic.response import text
from sanic.response import json

app = Sanic("My Hello, world app")


app.static("/favicon.ico", "server/static/favicon.png")
app.static("/static", "server/static/")



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


@app.websocket("/realtime/<room>")
async def realtime(request, ws, room):
    msg = "hello"
    while True:
        await ws.send(msg)
        msg = await ws.recv()


@app.get("/subscribe")
async def subscribe(request):
    symbols = request.args.getlist("symbols")
    pass


@app.get("/unsubscribe")
async def unsubscribe(request):
    symbols = request.args.getlist("symbols")
    pass

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1234, debug=True)
