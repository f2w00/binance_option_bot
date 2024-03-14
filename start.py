import json
import time
import logging
from binance_interface.api import EO, PM
from flask import Flask, request

# 打开配置json文件
with open("settings.json", 'r', encoding = 'UTF-8') as f:
    setting_dict = json.load(f)

# logging config
logging.basicConfig(filename = time.strftime("%Y-%m-%d", time.localtime()) + '-log.txt',
                    format = '%(asctime)s  %(filename)s : %(levelname)s  %(message)s',
                    filemode = 'a',
                    level = logging.DEBUG)


def log_to_txt(flag, text, **params):
    if flag == 0:
        logging.info(text, **params)
    if flag == 1:
        logging.error(text, **params)


# 设置币安
class BinanceClient(object):

    client = EO(setting_dict['binance_key'], setting_dict['binance_secret'])
    account = PM(setting_dict['binance_key'], setting_dict['binance_secret'])
    # 记录下单的id,状态,次数,如果当天次数过多不允许下单并且邮件汇报
    pyramid_dict = {
        'long': {'orderId': [], 'status': 0, 'freq': 0},
        'short': {'orderId': [], 'status': 0, 'freq': 0}
    }

    @staticmethod
    def open_order(symbol_input,
                   side,
                   type_input,
                   quantity,
                   price_input,
                   timeinforce = 'GTC',
                   clear_freq_date = False):
        """
            通过输入的参数来确定下单的具体情况,并限制同一个方向上的开单,例如已有多单,那么就取消前一个订单,再开单
            限制开单频率,通过
            @param symbol_input:用来确认交易对,例如BTCUSDT
            @param side:确认方向,buy和sell
            @param type_input:订单类型,limit
            @param quantity:下单数量
            @param price_input: 委托价格
            @param timeinforce:有效时间,例如GTC,good till cancel 直到成交为止
            @param clear_freq_date: 用来确认是否清除一个方向上的订单
        """
        try:
            order_reply = None
            if side == 'buy':
                if BinanceClient.pyramid_dict['long']['status'] <= setting_dict[
                    'pyramid']:
                    order_reply = BinanceClient.client.accountTrade.set_order(symbol = symbol_input,
                                                                              side = side,
                                                                              type = type_input,
                                                                              quantity = quantity,
                                                                              timeInForce = timeinforce,
                                                                              price = price_input)
                else:
                    BinanceClient.client.accountTrade.cancel_order(symbol = symbol_input,
                                                                   orderId =
                                                                   BinanceClient.pyramid_dict[
                                                                       'long']['orderId'][
                                                                       -1])

                    BinanceClient.pyramid_dict['long']['orderId'].pop()
                    BinanceClient.pyramid_dict['long']['status'] -= 1
                    order_reply = BinanceClient.client.accountTrade.set_order(symbol = symbol_input,
                                                                              side = side,
                                                                              type = type_input,
                                                                              quantity = quantity,
                                                                              timeInForce = timeinforce,
                                                                              price = price_input)
                BinanceClient.pyramid_dict['long']['orderId'].push(
                    order_reply['data']['orderId'])
                BinanceClient.pyramid_dict['long']['status'] += 1
                # BinanceClient.pyramid_dict['long']['orderId'] = order_reply['data']['orderId']
                if clear_freq_date:
                    BinanceClient.pyramid_dict['long']['freq'] = 0
                BinanceClient.pyramid_dict['long']['freq'] += 1
                if BinanceClient.pyramid_dict['long']['freq'] >= setting_dict[
                    'most_freq']:
                    """发送邮件"""
                    pass
                """
                {'code': 200,
                 'data': {
                            'symbol': 'MANAUSDT',
                            'orderId': 2207382482,
                            'orderListId': -1,
                            'clientOrderId': 'P3PQXqOCmLmvSgT3bHpNhY',
                            'transactTime': 1706119355892,
                            'price': '0.40000000',
                            'origQty': '15.00000000',
                            'executedQty': '0.00000000',
                            'cummulativeQuoteQty': '0.00000000',
                            'status': 'NEW',
                            'timeInForce': 'GTC',
                            'type': 'LIMIT',
                            'side': 'BUY',
                            'workingTime': 1706119355892,
                            'fills': [],
                            'selfTradePreventionMode': 'EXPIRE_MAKER'},
                            'msg': ''
                        }
                """
            elif side == 'sell':
                if BinanceClient.pyramid_dict['short']['status'] <= setting_dict[
                    'pyramid']:
                    order_reply = BinanceClient.client.accountTrade.set_order(symbol = symbol_input,
                                                                              side = side,
                                                                              type = type_input,
                                                                              quantity = quantity,
                                                                              timeInForce = timeinforce,
                                                                              price = price_input)
                else:
                    BinanceClient.close_order(symbol_input, BinanceClient.pyramid_dict[
                        'short']['orderId'][-1])
                    order_reply = BinanceClient.client.accountTrade.set_order(symbol =
                                                                              symbol_input,
                                                                              side = side,
                                                                              type = type_input,
                                                                              quantity = quantity,
                                                                              timeInForce = timeinforce,
                                                                              price = price_input)
                BinanceClient.pyramid_dict['short']['status'] += 1
                BinanceClient.pyramid_dict['short']['orderId'].push(
                    order_reply['data']['orderId'])
                if clear_freq_date:
                    BinanceClient.pyramid_dict['short']['freq'] = 0
                BinanceClient.pyramid_dict['short']['freq'] += 1
                if BinanceClient.pyramid_dict['short']['freq'] >= setting_dict[
                    'most_freq']:
                    """发送邮件"""
                    pass
            if order_reply:
                log_to_txt(0, str(order_reply))
        except Exception as e:
            log_to_txt(1, str(e))
        finally:
            log_to_txt(0,
                       'trade',
                       *[symbol_input, side, type_input, quantity, timeinforce])

    @staticmethod
    def close_order(symbol_input, order_id):
        try:
            BinanceClient.client.accountTrade.cancel_order(symbol = symbol_input,
                                                           orderId = order_id)

            if order_id in BinanceClient.pyramid_dict['short']['orderId']:
                BinanceClient.pyramid_dict['short']['status'] -= 1
                BinanceClient.pyramid_dict['short']['orderId'].remove(order_id)
            if order_id in BinanceClient.pyramid_dict['long']['orderId']:
                BinanceClient.pyramid_dict['long']['status'] -= 1
                BinanceClient.pyramid_dict['long']['orderId'].remove(order_id)
        except Exception as e:
            log_to_txt(0, str(e))

    @staticmethod
    def get_account_info():
        try:
            return BinanceClient.account.account.get_account()
        except Exception as e:
            print(e)
            log_to_txt(1, str(e))


# flask setting
app = Flask(__name__)
print('running server from now on ' + time.strftime("%Y-%m-%d %H:%M:%S",
                                                    time.localtime()))


@app.post('/open')
def route_open_order():
    try:
        symbol = request.json['symbol']
        side = request.json['side']
        type_input = request.json['type']
        quantity = request.json['quantity']
        price = request.json['price']
        BinanceClient.open_order(symbol, side, type_input, quantity, price)
        BinanceClient.open_order(symbol, 'sell' if side == 'buy' else 'buy', type_input,
                                 quantity, price)
    except Exception as e:
        log_to_txt(1, str(e))


@app.route('/close')
def route_close_order():
    try:
        symbol = request.json['symbol']
        side = request.json['side']
        BinanceClient.close_order(symbol, BinanceClient.pyramid_dict[side]['orderId'][-1])
        # BinanceClient.close_order()
    except Exception as e:
        log_to_txt(1, str(e))


@app.get('/account_info')
def route_get_account():
    try:
        return BinanceClient.get_account_info()
    except Exception as e:
        print(e)
        log_to_txt(1, str(e))


@app.route('/nice')
def route_nice():
    return 'Nice to meet you!'


if __name__ == '__main__':
    # print('running server from now on ' + time.strftime("%Y-%m-%d %H:%M:%S", 
    # time.localtime()))
    app.run(port = 8012, host = '0.0.0.0')
