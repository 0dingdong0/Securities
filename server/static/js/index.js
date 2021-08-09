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


const data = {}
let socket = undefined

window.onload = function () {
    update_ui_size()
    window.onresize = update_ui_size
    // let date = moment().format('YYYYMMDD')
    let date = '20210809'

    let timestamp = moment().unix()
    let init = true

    console.log(`today is ${date}`)

    let params = {
        init: init,
        // 'timestamp' : 1626059575
    }

    let zhangting = new Zhangting(date, '#zhangting')
    let zhangsu = new Zhangsu(date, '#zhangsu')
    let stocks = new Stocks(date, '#stock-list')

    axios.get(`/market/${date}`, { 'params': params })
        .then((response) => {

            socket = new WebSocket(`ws://127.0.0.1:8000/websocket/${moment().format('x')}`)
            socket.onopen = function (event) {
                socket.send("Hello!");
            };
            socket.onmessage = function (event) {
                // console.log(event.data);
                // let result = JSON.parse(event.data)
                let result = eval(`(${event.data})`)
                if(result.cmd == 'snapshot'){
                    if(!(result.date in data)){
                        return
                    }
                    let dailydata = data[result.date]
                    result.zt_status = result.zt_status.filter(
                        item => !dailydata.names[item[0]].includes('ST')
                    )
                    result.zt_status.sort((a, b) => a[1] ? a[1] - b[1] : -1)

                    dailydata['zf_indices'] = result.zf_indices
                    dailydata['zhangfu'] = result.zhangfu
                    dailydata['zs_indices'] = result.zs_indices
                    dailydata['zhangsu'] = result.zhangsu
                    dailydata['lb_indices'] = result.lb_indices
                    dailydata['liangbi'] = result.liangbi
                    dailydata['snapshot'] = result.snapshot
                    
                    zhangting.add_symbols(result.zt_status, result.check_point_idx)
                    zhangsu.update()
                    stocks.update()
                }

                console.log(result);
            };
            socket.onclose = function (event) {
                console.log('closed')
            };
            socket.onerror = function (e) { console.log(e) }

            console.log('-----------------------', response)

            let result = response.data
            if(typeof(result) === 'string'){
                result = eval(`(${result})`)
            }
            if (!(result.date in data)) {
                data[result.date] = {
                    'check_points': result.check_points,
                    'names': result.names,
                    'symbols': result.symbols,
                    'mcap': result.mcap,
                    'zhishu': result.zhishu,
                    'symbol_zhishu': {},
                    // 'zt_indices': result.zt_indices.filter(
                    //     idx => !result.names[idx].includes('ST')
                    // ),
                    'zf_indices': result.zf_indices,
                    'zs_indices': result.zs_indices,
                    'lb_indices': result.lb_indices,
                    'zhangfu': result.zhangfu,
                    'zhangsu': result.zhangsu,
                    'liangbi': result.liangbi,
                    'snapshot': result.snapshot
                }
                
                let zt_status = result.zt_status.filter(
                    item => !result.names[item[0]].includes('ST')
                )
                zt_status.sort((a, b) => a[1] - b[1])

                for (let symbol_zs in result.zhishu) {
                    let name_zs = result.zhishu[symbol_zs].name
                    for (let symbol of result.zhishu[symbol_zs].codes) {
                        if (!(symbol in data[result.date].symbol_zhishu)) {
                            data[result.date].symbol_zhishu[symbol] = []
                        }
                        data[result.date].symbol_zhishu[symbol].push([symbol_zs, name_zs])
                    }

                }
                zhangting.add_symbols(zt_status, result.check_point_idx)
                zhangsu.update()
                stocks.update()
            }
            
            console.log(data)
        }).catch((error) => {
            console.log(error)
        })

}

class Stocks {
    constructor(date, container_selector){
        this.date = date
        this.sort_column = 'zhangfu'
        this.ascending = false
        this.stocks = d3.select(`${container_selector} tbody`)

        let that = this
        this.stocks.on('click', (e)=>{
            if(e.target.tagName !== 'TD'){
                return
            }

            let column = undefined
            if(e.target.classList.contains('liangbi')){
                column = 'liangbi'
            }else if(e.target.classList.contains('zhangfu')){
                column = 'zhangfu'
            }

            if(!column){
                return
            }

            if(column === that.sort_column){
                that.ascending = !that.ascending
            }else{
                that.sort_column = column
            }

            that.update()
        })
    }

    update(){
        let dd = data[this.date]
        let data_stocks = []

        let indices = undefined
        if(this.sort_column == 'zhangfu'){
            indices = dd.zf_indices
        }else if(this.sort_column == 'liangbi'){
            indices = dd.lb_indices
        }
        
        if(!this.ascending){
            indices = indices.slice().reverse()
        }

        for(let _ of indices.slice(0,100)){
            let symbol = dd.symbols[_]
            let name = dd.names[_]
            let zhangfu = dd.zhangfu[_].toFixed(2)
            let liangbi = dd.liangbi[_].toFixed(1)
            let now = dd.snapshot[_][2]
            let mcap = dd.mcap[_]
            data_stocks.push([symbol, name, now, zhangfu, liangbi, mcap])
        }

        this.stocks.selectAll('tr')
            .data(data_stocks)
            .join('tr')
            .attr('class', d=>d[0])
            .html(d=>`<td class="symbol">${d[0]}</td><td class="name">${d[1]}</td><td class="now">${d[2]}</td><td class="zhangfu">${d[3]}</td><td class="liangbi">${d[4]}</td><td class="mcap">${d[5]}</td>`)
    }
}

class Zhangsu {
    constructor(date, container_selector){
        this.date = date
        this.zhishu = d3.select(`${container_selector} #zhangsu-zhishu tbody`)
        this.stocks = d3.select(`${container_selector} #zhangsu-stocks tbody`)
    }

    update(){
        let dd = data[this.date]

        let data_stocks = []
        let data_zhishu = {}
        for(let _ of dd.zs_indices.slice(-30)){
            let symbol = dd.symbols[_]
            let name = dd.names[_]



            if(dd.zhangsu[_]<2){
                continue
            }

            let zhangfu = dd.zhangfu[_].toFixed(2)
            let zhangsu = dd.zhangsu[_].toFixed(2)
            data_stocks.unshift([symbol, name, zhangfu, zhangsu])
            
            for (let [symbol_zhishu, name_zhishu] of dd.symbol_zhishu[symbol]) {
                if (!(symbol_zhishu in data_zhishu)) {
                    data_zhishu[symbol_zhishu] = [symbol_zhishu, name_zhishu, 1 ]
                } else {
                    data_zhishu[symbol_zhishu][2]++
                }
            }
        }
        this.stocks.selectAll('tr')
            .data(data_stocks)
            .join('tr')
            .attr('class', d=>d[0])
            .html(d=>`<td class="symbol">${d[0]}</td><td class="name">${d[1]}</td><td class="zhangfu">${d[2]}</td><td class="zhangsu">${d[3]}</td>`)

        this.zhishu.selectAll('tr')
            .data(Object.values(data_zhishu).sort((a, b) => b[2] - a[2]))
            .join('tr')
            .attr('class', d => d[0])
            .html(d => `<td class="name">${d[1]}</td><td class="count">${d[2]}</td>`)

    }
}

class Zhangting {

    constructor(date, parent_selector, left_margin = 10, top_margin = 5, bottom_margin = 5, right_margin = 70) {

        this.date = date
        this.status = [left_margin]
        this.stocks = []
        this.indices = []
        this.zhishu = {}

        this.left_margin = left_margin
        this.right_margin = right_margin
        this.top_margin = top_margin
        this.bottom_margin = bottom_margin

        this.div_parent = document.querySelector(parent_selector)
        console.log(this.div_parent.clientHeight)
        this.svg = d3.select(parent_selector).select('svg')
        this.svg.attr('width', this.div_parent.clientWidth).attr('height', this.div_parent.clientHeight)

        this.draw_axis()
    }

    draw_axis() {
        let width = parseInt(this.svg.attr('width'))
        let height = parseInt(this.svg.attr('height'))

        this.xscale = d3.scaleLinear().domain([0, 14400]).range([this.left_margin, width - this.right_margin])
        this.yscale = d3.scaleLinear().domain([0, 100]).range([this.top_margin, this.top_margin + 2000])

        let count = 8
        let step = (width - this.left_margin - this.right_margin) / count
        let lines = []

        for (let i = 0; i <= count; i++) {
            let x = this.left_margin + i * step
            let y1 = this.top_margin
            let y2 = height - this.bottom_margin

            lines.push([x, y1, x, y2])
        }

        this.svg.select('g.time-lines')
            .selectAll("line")
            .data(lines)
            .join('line')
            .attr('x1', d => d[0])
            .attr('y1', d => d[1])
            .attr('x2', d => d[2])
            .attr('y2', d => d[3])
            .style('stroke', (d, i) => i == 4 ? 'lightgrey' : 'gray')
            .style('stroke-width', 0.5)
    }

    add_symbols(zt_status, check_point_idx) {
        let start = moment()
        let dd = data[this.date]
        let timestamp_093000 = moment(`${this.date} 09:30:00`, 'YYYYMMDD hh:mm:ss').unix()

        let y_max = this.top_margin
        this.zhishu = {}
        for (let [symbol_idx, timestamp, not_lanban] of zt_status) {

            let symbol = dd.symbols[symbol_idx]
            let _ = this.indices.indexOf(symbol_idx)

            if( _ !== -1 ){
                this.stocks[_][5] = not_lanban === 1
            }else{
                if(!timestamp){
                    timestamp = dd.check_points[check_point_idx-1]
                }

                let xd = timestamp - timestamp_093000
                if (xd < 0) {
                    xd = 0
                } else if (xd > 7200 && xd < 7500) {
                    xd = 7200
                } else if (xd >= 12300 && xd < 12600) {
                    xd = 12600
                } else if (xd >= 12600 && xd <= 19800) {
                    xd = xd - 5400
                } else if (xd > 19800) {
                    xd = 14400
                }
    
                let x = this.xscale(xd)
                let y = undefined
                for (let yd = 0; yd < this.status.length; yd++) {
                    if (x >= this.status[yd]) {
                        y = this.yscale(yd)
                        this.status[yd] = x + 70
                        break
                    }
                }
    
                if (!y) {
                    this.status.push(this.left_margin + 70)
                    y = this.yscale(this.status.length - 1)
                    if (y > y_max) {
                        y_max = y
                    }
                }
    
                this.stocks.push([x, y, symbol, dd.names[symbol_idx], timestamp, not_lanban === 1])
                this.indices.push(symbol_idx)
                // console.log(x, y, symbol_idx, dd.symbols[symbol_idx], dd.names[symbol_idx], timestamp, moment.unix(timestamp).format())
    
            }

            for (let [symbol_zhishu, name_zhishu] of dd.symbol_zhishu[symbol]) {
                if (!(symbol_zhishu in this.zhishu)) {
                    this.zhishu[symbol_zhishu] = { 'name': name_zhishu, 'symbol': symbol_zhishu, 'count': 1, 'count_lanban': 0 }
                } else {
                    this.zhishu[symbol_zhishu].count++
                }

                if (not_lanban !== 1) {
                    this.zhishu[symbol_zhishu].count_lanban++
                }
            }
        }

        // console.log(Object.values(this.zhishu).sort((a, b) => b.count - a.count))

        if (y_max > (parseInt(this.svg.attr('height')) - this.top_margin - this.bottom_margin)) {
            this.svg.attr('height', y_max + this.top_margin + this.bottom_margin + 15)
            this.draw_axis()
        }

        d3.select('#zhangting .stocks')
            .selectAll('span')
            .data(this.stocks)
            .join('span')
            .attr('class', d => d[5] ? d[2] : `${d[2]} lanban`)
            .attr('style', d => `left:${d[0]}px;top:${d[1]}px;`)
            .text(d => d[3])

        d3.select('#zhishu tbody')
            .selectAll('tr')
            .data(Object.values(this.zhishu).sort((a, b) => b.count - a.count))
            .join('tr')
            .attr('class', d => d.symbol)
            .html(d => `<td class="name">${d.name}</td><td class="double-count">${d.count - d.count_lanban}/${d.count}</td>`)

        console.log('Zhangting.add_symbols() used time:', moment()-start, 'ms')
    }

}

let update_ui_size = function(){
    let width_zhangting_panel = document.querySelector('#zhangting-panel').clientWidth
    let height_zhangting_panel = document.querySelector('#zhangting-panel').clientHeight
    
    document.querySelector('#stock-lists').setAttribute('style', `height:${window.innerHeight - height_zhangting_panel}px`)
}