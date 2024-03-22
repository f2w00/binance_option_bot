import datetime
import json
import logging
import math
import time

from binance_interface.api import EO
from okx import Account, PublicData, Trade
from tinydb import TinyDB

# 打开配置json文件
with open("settings.json", 'r', encoding = 'UTF-8') as f:
    setting_dict = json.load(f)
db = TinyDB('db.json')
if len(db.all()) == 0:
    db.insert({
        "pyramid": {
            'long': {
                'orders': [],
                'status': 0,
                'freq': 0,
            }, 'short': {
                'orders': [],
                'status': 0,
                'freq': 0,
            }
        }
    })


class BinanceInterface(object):
    client = EO(setting_dict['binance_key'], setting_dict['binance_secret'])

    @staticmethod
    def open_order(symbol,
                   quantity,
                   side = 'buy',
                   price_input = '',
                   type_input = 'BBO',
                   timeinforce = 'GTC'):
        return BinanceInterface.client.accountTrade.set_order(symbol = symbol,
                                                              side = side,
                                                              type = type_input,
                                                              quantity = quantity,
                                                              timeInForce = timeinforce,
                                                              price = price_input)

    @staticmethod
    def close_order(symbol, orderId):
        result = BinanceInterface.client.accountTrade.close_order(symbol = symbol,
                                                                  orderId = orderId)
        return result

    @staticmethod
    def account_info():
        return BinanceInterface.client.accountTrade.get_account()

    @staticmethod
    def account_available(asset = 'USDT'):

        response = BinanceInterface.client.accountTrade.get_account()
        available = 0
        for i in response['data']['asset']:
            if i['asset'] == asset:
                available = i['available']
                break
        return float(available)

    @staticmethod
    def exchange_info(base_filter = 2,
                      side_filter = 'CALL',
                      date_filter = 2,
                      minQty_filter = '0.01'):
        now_time = int(time.time() * 1000)
        request_result = BinanceInterface.client.market.get_exchangeInfo()

        def filter_my(x):
            if x['side'] == side_filter and x['contractId'] == base_filter and x[
                'expiryDate'] - now_time <= date_filter * 86400000 and x[
                'minQty'] == minQty_filter:
                return x

        symbols_array = list(filter(filter_my, request_result['data']['optionSymbols']))
        return symbols_array

    @staticmethod
    def proper_symbol(data_array, strike_price, side):
        proper_symbol = None
        min_delta = 99999999999
        factor = 1 if side == 'BUY' else -1
        for i in data_array:
            if abs(float(i['strikePrice']) - strike_price) < min_delta and (
                    float(i['strikePrice']) - strike_price) * factor >= 0:
                min_delta = abs(float(i['strikePrice']) - strike_price)
                proper_symbol = i['symbol']
        return proper_symbol

    @staticmethod
    def mark_price(symbol):
        return BinanceInterface.client.market.get_mark(symbol)['data'][0]['markPrice']

    @staticmethod
    def all_params(side, price):
        exchange_info = BinanceInterface.exchange_info(
            base_filter = 2,
            side_filter = 'CALL' if side == 'BUY' else 'PUT',
            date_filter = 1)
        final_available = float(BinanceInterface.account_available() * setting_dict[
            'order_rate'])
        symbol = str(BinanceInterface.proper_symbol(exchange_info, price, side))
        mark_price = float(BinanceInterface.mark_price(symbol))
        target_quantity = math.floor((final_available / mark_price) * 100) / 100
        quantity = 0.01 if target_quantity < 0.01 else target_quantity
        return {
            'symbol': symbol,
            'quantity': quantity,
            'type_input': 'BBO',
            'side': side
        }


class OkxInterface(object):
    client = Trade.TradeAPI(setting_dict['okx_key'],
                            setting_dict['okx_secret'],
                            passphrase = setting_dict['okx_passphrase'],
                            flag = setting_dict['okx_flag'])
    account = Account.AccountAPI(setting_dict['okx_key'],
                                 setting_dict['okx_secret'],
                                 passphrase = setting_dict['okx_passphrase'],
                                 flag = setting_dict['okx_flag'])
    data = PublicData.PublicAPI(setting_dict['okx_key'],
                                setting_dict['okx_secret'],
                                passphrase = setting_dict['okx_passphrase'],
                                flag = setting_dict['okx_flag'])

    @staticmethod
    def open_order(symbol, quantity):
        # todo tdMode确认,markprice确认,side确认,账户余额确认
        result = OkxInterface.client.place_order(instId = symbol,
                                                 tdMode = 'cash',
                                                 side = 'buy',
                                                 ordType = 'market', sz = quantity)
        format_result = {'code': '-1', 'data': result}
        if len(result['data']) > 0 and result['code'] == '0':
            format_result = {
                'code': result['code'],
                'data': {
                    'orderId': result['data'][0]['ordId'],
                    'symbol': symbol,
                    'quantity': quantity
                }
            }
        return format_result

    @staticmethod
    def close_order(symbol, orderId):
        result = OkxInterface.client.cancel_order(instId = symbol, ordId = orderId)
        print(result)
        format_result = {'code': '0' if result['code'] == '0' else '-1', 'data': result}
        return format_result

    @staticmethod
    def account_info():
        return OkxInterface.account.get_account_config()

    @staticmethod
    def account_available():
        # fixme 确认账户余额形式
        result = OkxInterface.account.get_account_balance()
        if len(result['data']) > 0 and len(result['data'][0]['details']) > 0:
            return float(result['data'][0]['details'][0]['availBal'])
        return 20

    @staticmethod
    def exchange_info(side_filter = 'C', date_filter = 2):
        result = OkxInterface.data.get_instruments(instType = 'OPTION', uly = 'BTC-USD')[
            'data']
        now_time = int(time.time() * 1000)

        def filter_my(x):
            if (x['optType'] == side_filter and float(
                    x['expTime']) - now_time <= date_filter * 86400000):
                return x

        symbols_array = list(filter(filter_my, result))
        return symbols_array

    @staticmethod
    def proper_symbol(data_array, strike_price, side):
        proper_symbol = None
        min_delta = 99999999999
        factor = 1 if side == 'buy' else -1
        for i in data_array:
            if abs(float(i['stk']) - strike_price) < min_delta and (
                    float(i['stk']) - strike_price) * factor >= 0:
                min_delta = abs(float(i['stk']) - strike_price)
                proper_symbol = i['instId']
        return proper_symbol

    @staticmethod
    def mark_price(symbol = ''):
        result = OkxInterface.data.get_mark_price(instType = 'OPTION', instId = symbol)
        if len(result['data']) > 0:
            return float(result['data'][0]['markPx'])
        else:
            return -1

    @staticmethod
    def all_params(side, price):
        exchange_info = OkxInterface.exchange_info('C' if side == 'buy' else 'P')
        final_available = float(OkxInterface.account_available() * setting_dict[
            'order_rate'])
        symbol = str(OkxInterface.proper_symbol(exchange_info, price, side))
        mark_price = float(OkxInterface.mark_price(symbol))
        target_quantity = math.floor((final_available / mark_price) * 100) / 100
        quantity = 0.01 if target_quantity < 0.01 else target_quantity
        return {
            'symbol': symbol,
            'quantity': quantity,
        }


# 设置币安
class OrderClient(object):

    # 记录下单的id,状态,次数,如果当天次数过多不允许下单并且邮件汇报
    pyramid_dict = db.all()[0]['pyramid']
    client = None
    match setting_dict['broker']:
        case 'binance':
            client = BinanceInterface
        case 'okx':
            client = OkxInterface

    @staticmethod
    def open_order(params):
        """
            * 通过输入的参数来确定下单的具体情况,并限制同一个方向上的开单,例如已有多单,那么就取消前一个订单,再开单
            * 限制开单频率,通过freq和date来确定是否是同一天交易的,同样在settings.json中设置,
                * 每次开单都会增加freq并检查date
                * 每次关闭订单并不会减少freq,只有在日期(日)和上一次的不同之后才会刷新freq
        """
        order_reply = {
            'data': {'orderId': '111111111', 'symbol': 'BTC-USD', 'quantity': 0.02},
        }
        # todo 真实开单需要注意:模拟盘:okxflag,order_reply修改,开单取消注释
        # order_reply = {'data': {}}
        direction = params['direction']
        params.pop('direction')
        open_params = OrderClient.all_params_open(params)  # {'symbol': symbol,'quantity': quantity,}
        # if OrderClient.pyramid_dict[direction]['status'] < setting_dict['pyramid']:
        #     order_reply = OrderClient.client.open_order(**open_params)
        # else:
        #     OrderClient.close_order(direction)
        #     order_reply = OrderClient.client.open_order(**open_params)
        if 'code' in order_reply and order_reply['code'] == '-1':
            logging.error(str(order_reply))
        elif 'orderId' in order_reply['data']:
            # 如果上一次开单时间不是今天,那么清空freq,然后设定日期将freq加一
            if len(OrderClient.pyramid_dict[direction]['orders']) > 0 and \
                    OrderClient.pyramid_dict[direction]['orders'][-1][
                        'date'] != datetime.date.today().day:
                OrderClient.pyramid_dict[direction]['freq'] = 0
            OrderClient.pyramid_dict[direction]['orders'].append({
                'orderId':
                    order_reply['data']['orderId'],
                "symbol": order_reply['data']['symbol'],
                'quantity': order_reply['data']['quantity'],
                'date': datetime.date.today().day
            }
            )
            OrderClient.pyramid_dict[direction]['status'] += 1
            OrderClient.pyramid_dict[direction]['freq'] += 1
            if OrderClient.pyramid_dict[direction]['freq'] >= setting_dict['most_freq']:
                # todo 发送邮件
                pass
            db.update({'pyramid': OrderClient.pyramid_dict})
        print(order_reply, OrderClient.pyramid_dict)
        return {'reply': order_reply, 'pyramid': OrderClient.pyramid_dict}

    @staticmethod
    def close_order(direction, orderId_input = None):
        symbol = None
        order_id = None
        orders: list = OrderClient.pyramid_dict[direction]['orders']
        if len(orders) == 0:
            logging.error('empty orders')
            return OrderClient.pyramid_dict[direction]
        if orderId_input:
            for i in range(len(orders)):
                if orders[i]['orderId'] == orderId_input:
                    order_id = orders[i]['orderId']
                    symbol = orders[i]['symbol']
                    break
        if order_id is None:
            order_id = orders[-1]['orderId']
            symbol = orders[-1]['symbol']
        # order_reply = OrderClient.client.close_order(symbol = symbol, orderId = order_id)
        order_reply = {'code': '0'}
        if 'code' in order_reply and order_reply['code'] == '-1':
            logging.error(str(order_reply))
        elif order_reply['code'] == '0':
            for i in range(len(orders)):
                if orders[i]['orderId'] == order_id:
                    del OrderClient.pyramid_dict[direction]['orders'][i]
                    break
            OrderClient.pyramid_dict[direction]['status'] -= 1
            db.update({'pyramid': OrderClient.pyramid_dict})
        return OrderClient.pyramid_dict[direction]

    @staticmethod
    def all_params_open(params):
        return OrderClient.client.all_params(**params)
