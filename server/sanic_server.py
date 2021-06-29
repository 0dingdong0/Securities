import time
from sanic import Sanic
from datetime import datetime
from sanic.response import text
from sanic.response import json

app = Sanic("My Hello, world app")


@app.get("/market/<date>")
async def market(request, date):
    ts = request.args.get("ts")
    if ts is None:
        ts = time.time()
    return text(f'daily_data(): {date} {ts} {request.id}')

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

@app.websocket("/realtime")
async def realtime(request, ws):
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
