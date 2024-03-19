import json
import logging
import time
import traceback

from flask import Flask, request

from trader import OrderClient

# todo 确认tv参数发送正确
# 打开配置json文件
with open("settings.json", 'r', encoding = 'UTF-8') as f:
    setting_dict = json.load(f)

# logging config
logging.basicConfig(filename = 'log.log',
                    format = '%(asctime)s  %(filename)s : %(levelname)s  %(message)s',
                    filemode = 'a',
                    level = logging.DEBUG)


def log_to_txt(flag, text):
    if flag == 0:
        logging.info(text)
    if flag == 1:
        logging.error(text)


# flask setting
app = Flask(__name__)
print('running server from now on ' + time.strftime("%Y-%m-%d %H:%M:%S",
                                                    time.localtime()))


@app.post('/open')
def route_open_order():
    try:
        params = json.loads(request.data)
        msg = 'success'
        if params['target'] == 'OPEN':
            side = params['side']
            price = params['strike_price']
            price_other_side = params['strike_price_other_side']
            final_param = OrderClient.all_params_open({'side': side, 'price': price})
            res1 = OrderClient.open_order(**final_param)
            final_param_other = OrderClient.all_params_open({
                'side': 'BUY' if side == 'SELL' else 'SELL',
                'price': price_other_side
            })
            res2 = OrderClient.open_order(**final_param_other)
            msg = str(res1) + str(res2)
        elif params['target'] == 'CLOSE':
            side = params['side']
            order_id = params['order_id'] if 'order_id' in params else None
            res3 = OrderClient.close_order(side, order_id)
            msg = str(res3)
        return msg
    except Exception as e:
        print(str(traceback.format_exc()))
        log_to_txt(1, str(traceback.format_exc()))
        return str(traceback.format_exc())
    finally:
        log_to_txt(0, str(OrderClient.pyramid_dict))


@app.get('/account_info')
def route_get_account():
    try:
        return OrderClient.get_account_info()
    except Exception as e:
        print(str(traceback.format_exc()))
        log_to_txt(1, str(traceback.format_exc()))


@app.get('/exchange_info')
def route_get_exchange_info():
    try:
        return OrderClient.get_proper_symbol(OrderClient.get_exchange_info(), 64000)
    except Exception as e:
        print(str(traceback.format_exc()))
        log_to_txt(1, str(traceback.format_exc()))


@app.get('/mark_price')
def route_mark_price():
    try:
        return OrderClient.get_mark_price(request.args.get('symbol'))
    except Exception as e:
        print(str(traceback.format_exc()))
        log_to_txt(1, str(traceback.format_exc()))


@app.get('/margin')
def route_margin():
    try:
        return str(OrderClient.get_account_available())
    except Exception as e:
        print(str(traceback.format_exc()))


if __name__ == '__main__':
    # print('running server from now on ' + time.strftime("%Y-%m-%d %H:%M:%S", 
    # time.localtime()))
    app.run(port = 8012, host = '0.0.0.0')
