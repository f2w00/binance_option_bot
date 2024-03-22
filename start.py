import json
import logging
import time
import traceback

from flask import Flask, request

from trader import OkxInterface, OrderClient

# todo 确认tv参数发送正确
# 打开配置json文件
with open("settings.json", 'r', encoding = 'UTF-8') as f:
    setting_dict = json.load(f)

# logging config
logging.basicConfig(filename = 'log.log',
                    format = '%(asctime)s  %(filename)s : %(levelname)s  %(message)s',
                    filemode = 'a',
                    level = logging.INFO)


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
            res1 = OrderClient.open_order({
                'direction': 'long' if side == 'buy' else 'short',
                'side': side,
                'price': price
            })
            res2 = OrderClient.open_order({
                'direction': 'long' if side == 'sell' else 'short',
                'side': 'buy' if side == 'sell' else 'sell',
                'price': price_other_side
            })
            msg = str(res1) + str(res2)
        elif params['target'] == 'CLOSE':
            direction = params['direction']
            order_id = params['order_id'] if 'order_id' in params else None
            res3 = OrderClient.close_order(direction, order_id)
            msg = str(res3)
        return msg
    except Exception as e:
        print(str(traceback.format_exc()))
        log_to_txt(1, str(traceback.format_exc()))
        return str(traceback.format_exc())
    finally:
        log_to_txt(0, str(OrderClient.pyramid_dict))


@app.get('/test')
def route_margin():
    try:
        return str(OkxInterface.mark_price('BTC-USD-240322-64000-C'))
    except Exception as e:
        print(str(traceback.format_exc()))


if __name__ == '__main__':
    # print('running server from now on ' + time.strftime("%Y-%m-%d %H:%M:%S", 
    # time.localtime()))
    app.run(port = 8012, host = '0.0.0.0')
