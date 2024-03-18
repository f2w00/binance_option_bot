import datetime
import json
import math
import time
import logging
import traceback

from binance_interface.api import EO, PM
from flask import Flask, request
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


class BinanceInterface(object):
    client = EO(setting_dict['binance_key'], setting_dict['binance_secret'])
    account = PM(setting_dict['binance_key'], setting_dict['binance_secret'])

    @staticmethod
    def open_order(symbol_input, side, type_input, quantity, price_input, timeinforce):
        return BinanceInterface.client.accountTrade.set_order(symbol = symbol_input,
                                                              side = side,
                                                              type = type_input,
                                                              quantity = quantity,
                                                              timeInForce = timeinforce,
                                                              price = price_input)

    @staticmethod
    def cancel_order(symbol_input, orderId):
        return BinanceInterface.client.accountTrade.cancel_order(symbol = symbol_input,
                                                                 orderId = orderId)

    @staticmethod
    def account_info():
        return BinanceInterface.client.accountTrade.get_account()

    @staticmethod
    def account_info():
        return BinanceInterface.client.accountTrade.get_account()['asset'][0][
            'marginBalance']

    @staticmethod
    def exchange_info():
        return BinanceInterface.client.market.get_exchangeInfo()

    @staticmethod
    def mark_price(symbol):
        return BinanceInterface.client.market.get_mark(symbol)[0]['markPrice']


# 设置币安
class OrderClient(object):

    # 记录下单的id,状态,次数,如果当天次数过多不允许下单并且邮件汇报
    pyramid_dict = {
        'long': {
            'orderId': [],
            'status': 0,
            'freq': 0,
            'date': datetime.date.today().day
        },
        'short': {
            'orderId': [],
            'status': 0,
            'freq': 0,
            'date': datetime.date.today().day
        }
    }
    client = None
    match setting_dict['broker']:
        case 'binance':
            client = BinanceInterface

    @staticmethod
    def open_order(symbol_input,
                   side,
                   type_input,
                   quantity,
                   price_input,
                   timeinforce = 'GTC'):
        """
            * 通过输入的参数来确定下单的具体情况,并限制同一个方向上的开单,例如已有多单,那么就取消前一个订单,再开单
            * 限制开单频率,通过freq和date来确定是否是同一天交易的,同样在settings.json中设置,
                * 每次开单都会增加freq并检查date
                * 每次关闭订单并不会减少freq,只有在日期(日)和上一次的不同之后才会刷新freq
            @param symbol_input:用来确认交易对,例如BTCUSDT
            @param side:确认方向,SELL和PUT
            @param type_input:订单类型,limit
            @param quantity:下单数量
            @param price_input: 委托价格(目标达到价格)
            @param timeinforce:有效时间,例如GTC,good till cancel 直到成交为止
        """
        try:
            order_reply = None
            direction = 'long' if side == 'SELL' else 'short'
            if OrderClient.pyramid_dict[direction]['status'] < setting_dict['pyramid']:
                order_reply = OrderClient.client.open_order(symbol_input,
                                                            side,
                                                            type_input,
                                                            quantity,
                                                            price_input,
                                                            timeinforce)
            else:
                OrderClient.client.cancel_order(symbol_input = symbol_input,
                                                orderId = OrderClient.pyramid_dict[
                                                    direction]['orderId'][
                                                    -1])
                order_reply = OrderClient.client.open_order(symbol_input,
                                                            side,
                                                            type_input,
                                                            quantity,
                                                            price_input,
                                                            timeinforce)

            # 添加记录
            OrderClient.pyramid_dict[direction]['orderId'].append(
                order_reply['data']['orderId'])
            OrderClient.pyramid_dict[direction]['status'] += 1
            # 如果时间不是今天,那么清空freq,然后设定日期将freq加一
            if OrderClient.pyramid_dict[direction]['date'] != datetime.date.today().day:
                OrderClient.pyramid_dict[direction]['freq'] = 0
            OrderClient.pyramid_dict[direction]['date'] = datetime.date.today().day
            OrderClient.pyramid_dict[direction]['freq'] += 1
            if OrderClient.pyramid_dict[direction]['freq'] >= setting_dict[
                'most_freq']:
                """发送邮件"""
                pass
            if order_reply:
                log_to_txt(0, str(order_reply))
        except Exception as e:
            log_to_txt(1, str(traceback.format_exc()))
        finally:
            log_to_txt(0, str(
                {
                    "symbol": symbol_input,
                    "price": price_input,
                    "side": side,
                    'type': type_input,
                    'quantity': quantity,
                    'timeinforce': timeinforce
                }))

    @staticmethod
    def close_order(symbol_input, order_id):
        try:
            OrderClient.client.cancel_order(symbol_input = symbol_input,
                                            orderId = order_id)
            if order_id in OrderClient.pyramid_dict['short']['orderId']:
                OrderClient.pyramid_dict['short']['status'] -= 1
                OrderClient.pyramid_dict['short']['orderId'].remove(order_id)
            if order_id in OrderClient.pyramid_dict['long']['orderId']:
                OrderClient.pyramid_dict['long']['status'] -= 1
                OrderClient.pyramid_dict['long']['orderId'].remove(order_id)
        except Exception as e:
            log_to_txt(0, str(traceback.format_exc()))

    @staticmethod
    def get_account_info():
        try:
            return OrderClient.client.account_info()
        except Exception as e:
            log_to_txt(1, str(traceback.format_exc()))

    @staticmethod
    def get_exchange_info(symbol):
        try:
            return OrderClient.client.exchange_info(symbol)
        except Exception as e:
            log_to_txt(1, str(traceback.format_exc()))

    @staticmethod
    def get_account_margin():
        try:
            return OrderClient.client.get_account_margin()
        except Exception as e:
            log_to_txt(1, str(traceback.format_exc()))

    @staticmethod
    def get_mark_price(symbol):
        try:
            return OrderClient.client.mark_price(symbol)
        except Exception as e:
            log_to_txt(1, str(traceback.format_exc()))


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
