
let socket = undefined


window.onload = function () {
    
    socket = new WebSocket(`ws://127.0.0.1:8000/charts/${moment().format('x')}`)
    socket.onopen = function (event) {
        socket.send('{"cmd": "Hello!"}');
    };
    socket.onmessage = function (event) {
        console.log(event.data);
        let result = JSON.parse(event.data)
        // let result = eval(`(${event.data})`)
        // if(result.cmd == 'snapshot'){
        //     if(!(result.date in data)){
        //         return
        //     }
        //     let dailydata = data[result.date]
        //     result.zt_status = result.zt_status.filter(
        //         item => !dailydata.names[item[0]].includes('ST')
        //     )
        //     result.zt_status.sort((a, b) => a[1] ? a[1] - b[1] : -1)

        //     dailydata['zf_indices'] = result.zf_indices
        //     dailydata['zhangfu'] = result.zhangfu
        //     dailydata['zs_indices'] = result.zs_indices
        //     dailydata['zhangsu'] = result.zhangsu
        //     dailydata['lb_indices'] = result.lb_indices
        //     dailydata['liangbi'] = result.liangbi
        //     dailydata['snapshot'] = result.snapshot
            
        //     zhangting.add_symbols(result.zt_status, result.check_point_idx)
        //     zhangsu.update()
        //     stocks.update()
        //     for(let list of custom_lists.stocks){
        //         list.update()
        //     }

        //     keep_selection()
        // }

        // console.log(result);
    };
    socket.onclose = function (event) {
        console.log('closed')
    };
    socket.onerror = function (e) { console.log(e) }
}