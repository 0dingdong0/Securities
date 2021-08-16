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

let date = '20210812'
const data = {}
let socket = undefined
let selected_symbols = []

window.onload = function () {
    update_ui_size()
    window.onresize = update_ui_size
    // let date = moment().format('YYYYMMDD')

    let timestamp = moment().unix()
    let init = true

    console.log(`today is ${date}`)

    let params = {
        init: init,
        // 'timestamp' : 1626059575
    }

    axios.get(`/market/${date}`, { 'params': params })
        .then((response) => {

            socket = new WebSocket(`ws://127.0.0.1:8000/websocket/${moment().format('x')}`)
            socket.onopen = function (event) {
                socket.send('{"cmd": "Hello!"}');
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
                    for(let list of custom_lists.stocks){
                        list.update()
                    }

                    keep_selection()
                }

                // console.log(result);
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
                date = result.date
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
                    'snapshot': result.snapshot,
                    'lists': result.lists
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
                for(let list of custom_lists.stocks){
                    list.update()
                }
                for(let list of custom_lists.zhishu){
                    list.update()
                }
                keep_selection()
            }
            
            console.log(data)
        }).catch((error) => {
            console.log(error)
        })

}

class CustomStocks{

    constructor(container_selector){
        this._temp = []
        this._removed = []
        this.selector = container_selector
        this.tbody = d3.select(`${container_selector} tbody`)
    }

    add(symbol){
        let dd = data[date]
        
        if(dd.lists.stocks[this.selector] && dd.lists.stocks[this.selector].map(e=>e[0]).indexOf(symbol) !== -1){
            return
        }

        let idx = dd.symbols.indexOf(symbol)
        this._temp.push(symbol)
        if(!(this.selector in dd.lists.stocks)){
            dd.lists.stocks[this.selector] = []
        }
        dd.lists.stocks[this.selector].push([symbol, dd.names[idx], moment().unix(), dd.snapshot[idx][2]])
        this.update()
    }

    mark_remove(){
        let dd = data[date]
        let symbols = dd.lists.stocks[this.selector].map(e=>e[0])
        for(let symbol of selected_symbols){
            if(!symbol.startsWith('8') && symbols.indexOf(symbol)!==-1){
                if(this._temp.indexOf(symbol)!==-1){
                    this._temp = this._temp.filter(e=>e!==symbol)
                    dd.lists.stocks[this.selector] = dd.lists.stocks[this.selector].filter(e=>e[0]!==symbol)
                }else{
                    this._removed.push(symbol)
                }
            }
        }
        this.update()
    }

    remove(symbols=[]){
        let dd = data[date]
        this._removed = this._removed.filter(e=>symbols.indexOf(e)!==-1)
        dd.lists.stocks[this.selector] = dd.lists.stocks[this.selector].filter(e=>symbols.indexOf(e[0])!==-1 || this._temp.indexOf(e[0])!==-1)
    }

    update(symbols=[]){
        if(symbols.length){
            this._temp = this._temp.filter( e => symbols.indexOf(e)===-1)
        }

        let dd = data[date]
        let list = []
        if(this.selector in dd.lists.stocks){
            list = dd.lists.stocks[this.selector]
        }
        
        let that = this
        this.tbody.selectAll('tr')
            .data(list)
            .join('tr')
            .attr('class', (d)=>{
                let cls = `_${d[0]}`
                if(that._temp.indexOf(d[0])!==-1){
                    cls = `${cls} not-saved`
                }
                if(that._removed.indexOf(d[0])!==-1){
                    cls = `${cls} removed`
                }
                
                if(selected_symbols.indexOf(d[0])!==-1){
                    cls = `${cls} selected`
                }
                return cls
            }).html(d=>`<td class="symbol">${d[0]}</td><td class="name">${d[1]}</td><td class="added-at">${moment.unix(d[2]).format('MM-DD HH:mm')}</td><td class="add-price">${d[3]}</td><td class="now">${dd.snapshot[dd.symbols.indexOf(d[0])][2]}</td>`)
    }
}

class CustomZhishu{

    constructor(container_selector){
        this._temp = []
        this._removed = []
        this.selector = container_selector
        this.tbody = d3.select(`${container_selector} tbody`)
    }

    add(symbol){
        let dd = data[date]
        
        if(dd.lists.zhishu[this.selector] && dd.lists.zhishu[this.selector].map(e=>e[0]).indexOf(symbol) !== -1){
            return
        }

        this._temp.push(symbol)
        if(!(this.selector in dd.lists.zhishu)){
            dd.lists.zhishu[this.selector] = []
        }
        
        dd.lists.zhishu[this.selector].push([symbol, dd.zhishu[symbol].name, moment().unix()])
        this.update()
    }

    mark_remove(){
        let dd = data[date]
        let symbols = dd.lists.zhishu[this.selector].map(e=>e[0])
        for(let symbol of selected_symbols){
            if(symbol.startsWith('8') && symbols.indexOf(symbol)!==-1){
                if(this._temp.indexOf(symbol)!==-1){
                    this._temp = this._temp.filter(e=>e!==symbol)
                    dd.lists.zhishu[this.selector] = dd.lists.zhishu[this.selector].filter(e=>e[0]!==symbol)
                }else{
                    this._removed.push(symbol)
                }
            }
        }
        this.update()
    }

    remove(symbols=[]){
        let dd = data[date]
        this._removed = this._removed.filter(e=>symbols.indexOf(e)!==-1)
        dd.lists.zhishu[this.selector] = dd.lists.zhishu[this.selector].filter(e=>symbols.indexOf(e[0])!==-1 || this._temp.indexOf(e[0])!==-1)
    }

    update(symbols=[]){
        if(symbols.length){
            this._temp = this._temp.filter( e => symbols.indexOf(e)===-1)
        }

        let dd = data[date]
        let list = []
        if(this.selector in dd.lists.zhishu){
            list = dd.lists.zhishu[this.selector]
        }
        
        let that = this
        this.tbody.selectAll('tr')
            .data(list)
            .join('tr')
            .attr('class', (d)=>{
                let cls = `_${d[0]}`
                if(that._temp.indexOf(d[0])!==-1){
                    cls = `${cls} not-saved`
                }
                if(that._removed.indexOf(d[0])!==-1){
                    cls = `${cls} removed`
                }
                
                if(selected_symbols.indexOf(d[0])!==-1){
                    cls = `${cls} selected`
                }
                console.log(cls)
                return cls
            }).html(d=>`<td class="symbol">${d[0]}</td><td class="name">${d[1]}</td><td class="added-at">${moment.unix(d[2]).format('MM-DD HH:mm')}</td>`)
    }
}

class Zhishu{
    constructor(container_selector){
        this.symbols = []
        this.tbody = d3.select(`${container_selector} tbody`)
    }
    update(){
        let dd = data[date]
        this.tbody.selectAll('tr')
            .data(this.symbols)
            .join('tr')
            .attr('class', d=>`_${d}`)
            .html(d=>`<td class="symbol">${d}</td><td class="name">${dd.zhishu[d].name}</td>`)
    }
}

class Stocks {
    constructor(container_selector){
        // this.date = date
        this.sort_column = 'zhangfu'
        this.ascending = false
        this.stocks = d3.select(`${container_selector} tbody`)
        this.indices = []

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
            }else if(e.target.classList.contains('now')){
                column = 'now'
            }else if(e.target.classList.contains('mcap')){
                column = 'mcap'
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

        let dd = data[date]
        let data_stocks = []

        
        let indices = undefined
        if(this.indices){
            indices = this.indices
        }else{
            indices = dd.zf_indices
        }
        
        for(let _ of indices){
            let symbol = dd.symbols[_]
            let name = dd.names[_]
            let zhangfu = dd.zhangfu[_]
            let liangbi = dd.liangbi[_]
            let now = dd.snapshot[_][2]
            let mcap = dd.mcap[_]
            data_stocks.push([symbol, name, now, zhangfu, liangbi, mcap])
        }

        let idx_sort = undefined
        if(this.sort_column == "zhangfu"){
            idx_sort = 3
        }else if(this.sort_column == "liangbi"){
            idx_sort = 4
        }else  if(this.sort_column == "now"){
            idx_sort = 2
        }else if(this.sort_column == "mcap"){
            idx_sort = 5
        }

        if(idx_sort){
            if(!this.ascending){
                data_stocks.sort((a,b)=>{return b[idx_sort]-a[idx_sort]})
            }else{
                data_stocks.sort((a,b)=>{return a[idx_sort]-b[idx_sort]})
            }
        }
        

        this.stocks.selectAll('tr')
            .data(data_stocks.slice(0, 500))
            .join('tr')
            .attr('class', d=>`_${d[0]}`)
            .html(d=>`<td class="symbol">${d[0]}</td><td class="name">${d[1]}</td><td class="now">${d[2]}</td><td class="zhangfu">${d[3].toFixed(2)}</td><td class="liangbi">${d[4].toFixed(1)}</td><td class="mcap">${d[5]}</td>`)
    }
}

class Zhangsu {
    constructor(container_selector){
        // this.date = date
        this.zhishu = d3.select(`${container_selector} #zhangsu-zhishu tbody`)
        this.stocks = d3.select(`${container_selector} #zhangsu-stocks tbody`)
    }

    update(){
        let dd = data[date]

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
            .attr('class', d=>`_${d[0]}`)
            .html(d=>`<td class="symbol">${d[0]}</td><td class="name">${d[1]}</td><td class="zhangfu">${d[2]}</td><td class="zhangsu">${d[3]}</td>`)

        this.zhishu.selectAll('tr')
            .data(Object.values(data_zhishu).sort((a, b) => b[2] - a[2]))
            .join('tr')
            .attr('class', d=>`_${d[0]}`)
            .html(d => `<td class="name">${d[1]}</td><td class="count">${d[2]}</td>`)

    }
}

class Zhangting {

    constructor(parent_selector, left_margin = 10, top_margin = 5, bottom_margin = 5, right_margin = 70) {

        // this.date = date
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
        let dd = data[date]
        let timestamp_093000 = moment(`${date} 09:30:00`, 'YYYYMMDD hh:mm:ss').unix()

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
            .attr('class', d => d[5] ? `_${d[2]}` : `_${d[2]} lanban`)
            .attr('style', d => `left:${d[0]}px;top:${d[1]}px;`)
            .text(d => d[3])

        d3.select('#zhishu tbody')
            .selectAll('tr')
            .data(Object.values(this.zhishu).sort((a, b) => b.count - a.count))
            .join('tr')
            .attr('class', d => `_${d.symbol}`)
            .html(d => `<td class="name">${d.name}</td><td class="double-count">${d.count - d.count_lanban}/${d.count}</td>`)

        console.log('Zhangting.add_symbols() used time:', moment()-start, 'ms')
    }

}



let zhangting = new Zhangting('#zhangting')
let zhangsu = new Zhangsu('#zhangsu')
let stocks = new Stocks('#stock-list')
let zhishu = new Zhishu('#zhishu-list')

let custom_lists = {
    'zhishu':[new CustomZhishu('#custom-zhishu-list-0'), new CustomZhishu('#custom-zhishu-list-1')],
    'stocks':[new CustomStocks('#custom-stocks-list-0'), new CustomStocks('#custom-stocks-list-1')]
}

let update_ui_size = function(){
    let width_zhangting_panel = document.querySelector('#zhangting-panel').clientWidth
    let height_zhangting_panel = document.querySelector('#zhangting-panel').clientHeight
    
    document.querySelector('#stock-lists').setAttribute('style', `height:${window.innerHeight - height_zhangting_panel}px`)
}

d3.select('body').on('click', (e)=>{
    let symbol = undefined
    let el = undefined
    if(e.target.tagName === "SPAN" && e.target.parentNode.parentNode.id == "zhangting"){
        el = e.target
    }else if(e.target.tagName === "TD"){
        el = e.target.parentNode
    }else if(e.target.tagName === "TR"){
        el = e.target
    }

    if(!el){
        return
    }

    let clicked = document.querySelector('.clicked')
    if(clicked){
        clicked.classList.remove('clicked')
    }
    let container = el.parentNode
    while(container.tagName !== 'DIV'){
        container = container.parentNode
    }
    container.classList.add('clicked')


    for(let cls of el.classList){
        if(/_\d\d\d\d\d\d/.test(`${cls}`)){
            symbol = cls.slice(1)
            break
        }
    }

    if(!symbol){
        return
    }

    let idx = selected_symbols.indexOf(symbol)
    if(!e.shiftKey){
        remove_class('selected')
        if(idx===-1){
            selected_symbols = [symbol]
            add_class('selected', selected_symbols)
        }else{
            selected_symbols.splice(idx,1)
        }
    }else{
        if(idx===-1){
            selected_symbols.push(symbol)
            add_class('selected', selected_symbols)
        }else{
            selected_symbols.splice(idx,1)
            remove_class('selected', [symbol])
        }
    }

    let dd = data[date]
    let relative_symbols = mark_relative()
    
    if(relative_symbols && !relative_symbols[0].startsWith('8')){
        stocks.indices = relative_symbols.map(item=>dd.symbols.indexOf(item)).filter(item=>item!==-1)
        stocks.update()
    }else if(relative_symbols && relative_symbols[0].startsWith('8')){
        zhishu.symbols = relative_symbols
        zhishu.update()
    }else{
        zhishu.symbols = []
        zhishu.update()
        stocks.indices = []
        stocks.update()
    }
})

function keep_selection(){
    add_class('selected', selected_symbols)
    mark_relative()
}

function mark_relative(){
    remove_class('relative')
    if(selected_symbols.length == 0){
        return
    }

    let dd = data[date]
    let symbols = undefined

    for(let symbol of selected_symbols){

        let _symbols = []
        if(symbol.startsWith('8')){
            _symbols = dd.zhishu[symbol].codes
        }else{
            _symbols = dd.symbol_zhishu[symbol].map(el=>el[0])
        }

        if(!symbols){
            symbols = _symbols
        }else{
            symbols = symbols.filter(x=>_symbols.includes(x))
        }

        if(symbols.length == 0){
            break
        }
    }

    if(symbols.length){
        add_class('relative', symbols)
        return symbols
    }
}

function add_class(class_name, symbols=undefined){
    let elements = []
    if(symbols && symbols.length>0){
        elements = document.querySelectorAll(symbols.map(e=>`._${e}`).join(','))
    }else{
        elements = document.querySelectorAll(`.${class_name}`)
    }
    
    for(let el of elements){
        el.classList.add(class_name)
    }
}
function remove_class(class_name, symbols=undefined){
    let elements = []
    if(symbols && symbols.length>0){
        elements = document.querySelectorAll(symbols.map(e=>`._${e}`).join(','))
    }else{
        elements = document.querySelectorAll(`.${class_name}`)
    }
    
    for(let el of elements){
        el.classList.remove(class_name)
    }
}
function toggle_class(class_name, symbols=undefined){
    let elements = []
    if(symbols && symbols.length>0){
        elements = document.querySelectorAll(symbols.map(e=>`._${e}`).join(','))
    }else{
        elements = document.querySelectorAll(`.${class_name}`)
    }
    
    for(let el of elements){
        el.classList.toggle(class_name)
    }
}

window.onkeyup = function(e){

    if(/Numpad\d/.test(e.code) && e.altKey){
        let idx = parseInt(e.key)

        for(let symbol of selected_symbols){
            if(symbol.startsWith('8') && idx < custom_lists.zhishu.length){
                custom_lists.zhishu[idx].add(symbol)
            }else if( !symbol.startsWith('8') && idx < custom_lists.stocks.length) {
                custom_lists.stocks[idx].add(symbol)
            }
        }
    }else if(e.code == 'KeyS' && e.shiftKey){

        let dd = data[date]
        let lists = {}
        
        for(let group in dd.lists){
            lists[group] = {}
            for(let key in dd.lists[group]){
                lists[group][key] = dd.lists[group][key].slice()
                for(let item of custom_lists[group]){
                    if(item.selector==key){
                        lists[group][key] = lists[group][key].filter(e=>item._removed.indexOf(e[0])===-1)
                    }
                }
            }
        }
        // console.log(lists)
        // return
        axios.patch('/lists', lists)
        .then((response) => {
            let symbols_zhishu = []
            console.log(response.data)
            for(let key in response.data.zhishu){
                for(let symbol of response.data.zhishu[key]){
                    symbols_zhishu.push(symbol[0])
                }
            }
            let symbols_stocks = []
            for(let key in response.data.stocks){
                for(let symbol of response.data.stocks[key]){
                    symbols_stocks.push(symbol[0])
                }
            }
            for(let item of custom_lists.zhishu){
                item.remove(symbols_zhishu)
                item.update(symbols_zhishu)
            }
            for(let item of custom_lists.stocks){
                item.remove(symbols_stocks)
                item.update(symbols_stocks)
            }
            for(let container of document.querySelectorAll('.save-needed')){
                container.classList.remove('save-needed')
            }
        }).catch((error) => {
            console.log(error)
        })

    }else if(e.code == 'Delete'){
        for(let item of custom_lists.zhishu){
                item.mark_remove()
        }
        for(let item of custom_lists.stocks){
                item.mark_remove()
        }
    }else if(e.code == 'ArrowUp' && e.ctrlKey){
        let container = document.querySelector('.clicked')
        if(!container){
            return
        }
        let id = container.getAttribute('id')
        if(!id.startsWith('custom-')){
            return
        }
        let group = id.split('-')[1]
        let save_needed = false
        for(let item of custom_lists[group]){

            if('#'+id !== item.selector){
                continue
            }
            let list = data[date].lists[group]['#'+id]
            let indices = []
            for(let _=0; _<list.length; _++ ){
                let item = list[_]
                let symbol = item[0]
                if(selected_symbols.indexOf(symbol)!==-1){
                    if(_==0){
                        indices.push(_)
                        continue
                    }
                    if(indices.indexOf(_-1)!==-1){
                        indices.push(_)
                        continue
                    }
                    let temp = list[_-1]
                    list[_-1] = list[_]
                    list[_] = temp
                    indices.push(_-1)
                    save_needed = true
                }
            }
            item.update()
            break
        }

        if(save_needed){
            container.classList.add('save-needed')
        }
    }else if(e.code == 'ArrowDown' && e.ctrlKey){
        let container = document.querySelector('.clicked')
        if(!container){
            return
        }
        let id = container.getAttribute('id')
        if(!id.startsWith('custom-')){
            return
        }
        let group = id.split('-')[1]
        let save_needed = false
        for(let item of custom_lists[group]){

            if('#'+id !== item.selector){
                continue
            }
            let list = data[date].lists[group]['#'+id]
            let indices = []
            for(let _=list.length-1; _>=0; _-- ){
                let item = list[_]
                let symbol = item[0]
                if(selected_symbols.indexOf(symbol)!==-1){
                    if(_==list.length-1){
                        indices.push(_)
                        continue
                    }
                    if(indices.indexOf(_+1)!==-1){
                        indices.push(_)
                        continue
                    }
                    let temp = list[_+1]
                    list[_+1] = list[_]
                    list[_] = temp
                    indices.push(_+1)
                    save_needed=true
                }
            }
            item.update()
            break
        }
        
        if(save_needed){
            container.classList.add('save-needed')
        }
    }else if(e.code == 'ArrowRight'){
        let symbols = ['002717', '300589']
        let message = {'cmd': 'charts', 'symbols': symbols}
        socket.send(JSON.stringify(message));
    }
}