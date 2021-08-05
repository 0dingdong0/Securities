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
        // 'timestamp' : 1626059575
    }

    axios.get(`/market/${date}`, {'params':params})
    .then((response)=>{
        console.log('-----------------------')
        console.log(response)
    }).catch((error)=>{
        console.log(error)
    })

    let zhangting = new Zhangting('#zhangting')
}



class Zhangting{
    constructor(parent_selector, left_margin=10, top_margin=10, bottom_margin=10, right_margin=70){
        this.left_margin = left_margin
        this.right_margin = right_margin
        this.top_margin = top_margin
        this.bottom_margin = bottom_margin

        this.div_parent = document.querySelector(parent_selector)
        this.svg = d3.select(parent_selector).select('svg')
        this.svg.attr('width', this.div_parent.clientWidth).attr('height', this.div_parent.clientHeight)

        this.draw_axis()
    }

    draw_axis(){
        let width = this.div_parent.clientWidth
        let height = this.div_parent.clientHeight

        let count = 8
        let step = (width-this.left_margin-this.right_margin)/count
        let lines = []

        for(let i=0; i<=count; i++){
            let x = this.left_margin+i*step
            let y1 = this.top_margin
            let y2 = height-this.bottom_margin

            lines.push([x, y1, x, y2])
        }

        this.svg.append('g')
                .attr('class', 'time-lines')
                .selectAll("line")
                .data(lines)
                .join('line')
                .attr('x1', d=>d[0])
                .attr('y1', d=>d[1])
                .attr('x2', d=>d[2])
                .attr('y2', d=>d[3])
                .style('stroke', (d,i)=> i==4 ? 'lightgrey' : 'gray')
                .style('stroke-width', 0.5)
    }


}