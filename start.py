import json
import logging
import time
import traceback

from flask import Flask, request

from trader import OrderClient

# todo 确认账户开通,确认tv参数发送正确
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
        if params['target'] == 'OPEN':
            symbol = params['symbol']
            side = params['side']
            price = params['price']
            price_other_side = params['price_other_side']
            # todo 确认quantity
            quantity = 0.01
            # quantity=math.floor(((OrderClient.get_account_info())*setting_dict[
            # 'order_rate']/OrderClient.get_mark_price(
            # symbol))*100)/100
            OrderClient.open_order(symbol, side, 'LIMIT', quantity, price)
            OrderClient.open_order(
                symbol,
                'BUY' if side == 'SELL' else 'SELL',
                'LIMIT',
                quantity,
                price_other_side)
        if params['target'] == 'CLOSE':
            symbol = params['symbol']
            side = params['side']
            direction = 'long' if side == 'SELL' else 'short'
            OrderClient.close_order(
                symbol,
                OrderClient.pyramid_dict[direction]['orderId'][-1])
    except Exception as e:
        log_to_txt(1, str(traceback.format_exc()))
    finally:
        log_to_txt(0, str(OrderClient.pyramid_dict))
        return 'success'


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
        return OrderClient.get_exchange_info()
    except Exception as e:
        print(str(traceback.format_exc()))
        log_to_txt(1, str(traceback.format_exc()))


@app.get('/mark_price')
def route_mark_price():
    try:
        return OrderClient.get_mark_price(request.args.get('symbol'))
    except Exception as e:
        log_to_txt(1, str(traceback.format_exc()))


@app.route('/nice')
def route_nice():
    return 'Nice to meet you!'


if __name__ == '__main__':
    # print('running server from now on ' + time.strftime("%Y-%m-%d %H:%M:%S", 
    # time.localtime()))
    app.run(port = 8012, host = '0.0.0.0')
