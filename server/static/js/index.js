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

window.onload = function () {
    let date = moment().format('YYYYMMDD')
    // let date = '20210712'

    let timestamp = moment().unix()
    let init = true

    console.log(`today is ${date}`)

    let params = {
        init: init,
        // 'timestamp' : 1626059575
    }

    let zhangting = new Zhangting(date, '#zhangting')

    axios.get(`/market/${date}`, { 'params': params })
        .then((response) => {
            console.log('-----------------------')
            console.log(response)
            let result = response.data
            if (!(result.date in data)) {
                data[result.date] = {
                    'names': result.names,
                    'symbols': result.symbols,
                    'zhishu': result.zhishu,
                    'symbol_zhishu': {},
                    'zt_indices': result.zt_indices.filter(
                        idx => !result.names[idx].includes('ST')
                    ),
                    'zt_status': result.zt_status.filter(
                        item => !result.names[item[0]].includes('ST')
                    )
                }

                data[result.date].zt_status.sort((a, b) => a[1] - b[1])

                for (let symbol_zs in result.zhishu) {
                    let name_zs = result.zhishu[symbol_zs].name
                    for (let symbol of result.zhishu[symbol_zs].codes) {
                        if (!(symbol in data[result.date].symbol_zhishu)) {
                            data[result.date].symbol_zhishu[symbol] = []
                        }
                        data[result.date].symbol_zhishu[symbol].push([symbol_zs, name_zs])
                    }

                }
            }
            console.log(data)
            zhangting.add_symbols(data[result.date].zt_status)
        }).catch((error) => {
            console.log(error)
        })

}

class Zhangting {

    constructor(date, parent_selector, left_margin = 10, top_margin = 5, bottom_margin = 5, right_margin = 70) {

        this.date = date
        this.status = [left_margin]
        this.stocks = []
        this.zhishu = {}

        this.left_margin = left_margin
        this.right_margin = right_margin
        this.top_margin = top_margin
        this.bottom_margin = bottom_margin

        this.div_parent = document.querySelector(parent_selector)
        this.svg = d3.select(parent_selector).select('svg')
        this.svg.attr('width', this.div_parent.clientWidth).attr('height', this.div_parent.clientHeight)

        this.draw_axis()
    }

    draw_axis() {
        let width = parseInt(this.svg.attr('width'))
        let height = parseInt(this.svg.attr('height'))

        this.xscale = d3.scaleLinear().domain([0, 14400]).range([this.left_margin, width - this.right_margin])
        this.yscale = d3.scaleLinear().domain([0, 100]).range([this.top_margin, this.top_margin + 2100])

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

    add_symbols(zt_status) {
        let dd = data[this.date]
        let timestamp_093000 = moment(`${this.date} 09:30:00`, 'YYYYMMDD hh:mm:ss').unix()

        let y_max = this.top_margin
        for (let [symbol_idx, timestamp, not_lanban] of zt_status) {

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

            // if (symbol_idx == 3708) {
            //     console.log(timestamp, timestamp_093000, timestamp - timestamp_093000, xd, x)
            // }

            if (!y) {
                this.status.push(this.left_margin + 70)
                y = this.yscale(this.status.length - 1)
                if (y > y_max) {
                    y_max = y
                }
            }

            let symbol = dd.symbols[symbol_idx]

            this.stocks.push([x, y, symbol, dd.names[symbol_idx], timestamp, not_lanban === 1])
            // console.log(x, y, symbol_idx, dd.symbols[symbol_idx], dd.names[symbol_idx], timestamp, moment.unix(timestamp).format())

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

        d3.select('#zhishu ul')
            .selectAll('li')
            .data(Object.values(this.zhishu).sort((a, b) => b.count - a.count))
            .join('li')
            .attr('class', d => d.symbol)
            .html(d => `<span>${d.name}</span><span>${d.count - d.count_lanban}/${d.count}</span>`)
    }

}