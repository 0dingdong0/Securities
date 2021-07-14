socket = new WebSocket('ws://127.0.0.1:8000/websocket/25948')
socket.onopen = function (event) {
    socket.send("Hello!");
};
socket.onmessage = function (event) {
    console.log(event.data);
};
socket.onclose = function (event) {
    console.log('closed')
};
socket.onerror = function (e) { console.log(e) }