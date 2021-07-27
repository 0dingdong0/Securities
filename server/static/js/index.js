// socket = new WebSocket('ws://127.0.0.1:8000/websocket/25948')
// socket.onopen = function (event) {
//     socket.send("Hello!");
// };
// socket.onmessage = function (event) {
//     console.log(event.data);
// };
// socket.onclose = function (event) {
//     console.log('closed')
// };
// socket.onerror = function (e) { console.log(e) }

// socket.addEventListener('open', function (event) {
//     socket.send('Hello Server!');
// });
// socket.addEventListener('message', function (event) {
//     console.log('Message from server ', event.data);
// });


window.onload = function(){
    // let date = moment().format('YYYYMMDD')
    let date = '20210712'
    
    let timestamp = moment()/1000
    let init = true

    console.log(`today is ${date}`)

    let params = {
        init: init,
        'timestamp' : 1626068690
    }

    axios.get(`/market/${date}`, {'params':params})
    .then((response)=>{
        console.log(response)
    }).catch((error)=>{
        console.log(error)
    })
}
