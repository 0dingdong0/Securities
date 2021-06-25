from sanic import Sanic
from sanic.response import text
from sanic.response import json

app = Sanic("My Hello, world app")


@app.get("/")
async def hello_world(request):
    return text("Hello, world!")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1234, debug=True)
