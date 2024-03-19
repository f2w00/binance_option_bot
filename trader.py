import datetime
import json
import math
import time

from binance_interface.api import EO

# 打开配置json文件
with open("settings.json", 'r', encoding = 'UTF-8') as f:
    setting_dict = json.load(f)


class BinanceInterface(object):
    client = EO(setting_dict['binance_key'], setting_dict['binance_secret'])

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
        # fixme 如果是BUY那么倾向于上升一档,如果是SELL倾向于下降一档
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
            'symbol_input': symbol,
            'quantity': quantity,
            'type_input': 'BBO',
            'side': side
        }


# 'long': {
#     'orders': [{
#         'orderId': 111111111,
#         'type': 'BBO',
#         'symbol': 'BTCUSDT-2022-600044',
#         'date': datetime.date.today().day
#     }],
#     'status': 0,
#     'freq': 0,
# }
# 设置币安
class OrderClient(object):

    # 记录下单的id,状态,次数,如果当天次数过多不允许下单并且邮件汇报
    pyramid_dict = {
        'long': {
            'orders': [],
            'status': 0,
            'freq': 0,
        },
        'short': {
            'orders': [],
            'status': 0,
            'freq': 0,
        }
    }
    client = None
    match setting_dict['broker']:
        case 'binance':
            client = BinanceInterface

    @staticmethod
    def open_order(symbol_input: str,
                   side: str,
                   type_input: str,
                   quantity: float,
                   price_input: float | None = None,
                   timeinforce = 'GTC'):
        """
            * 通过输入的参数来确定下单的具体情况,并限制同一个方向上的开单,例如已有多单,那么就取消前一个订单,再开单
            * 限制开单频率,通过freq和date来确定是否是同一天交易的,同样在settings.json中设置,
                * 每次开单都会增加freq并检查date
                * 每次关闭订单并不会减少freq,只有在日期(日)和上一次的不同之后才会刷新freq
            @param symbol_input:用来确认交易对,例如ETH-240329-600-C
            @param side:确认方向,SELL和BUY
            @param type_input:订单类型,LIMIT,BBO
            @param quantity:下单数量,float 两位小数,通常最小为0.01
            @param price_input: 委托价格(目标达到价格),适用于type=LIMIT的情况
            @param timeinforce:有效时间,例如GTC,good till cancel 直到成交为止
        """
        order_reply = {'data': {'orderId': 111111111}}
        direction = 'long' if side == 'SELL' else 'short'
        if OrderClient.pyramid_dict[direction]['status'] < setting_dict['pyramid']:
            order_reply = OrderClient.client.open_order(symbol_input,
                                                        side,
                                                        type_input,
                                                        quantity,
                                                        price_input,
                                                        timeinforce)
        else:
            OrderClient.close_order(side)
            order_reply = OrderClient.client.open_order(symbol_input,
                                                        side,
                                                        type_input,
                                                        quantity,
                                                        price_input,
                                                        timeinforce)
        if 'orderId' in order_reply['data']:
            # keypoint 添加记录
            # 如果上一次开单时间不是今天,那么清空freq,然后设定日期将freq加一
            if len(OrderClient.pyramid_dict[direction]['orders']) > 0 and \
                    OrderClient.pyramid_dict[direction]['orders'][-1][
                        'date'] != datetime.date.today().day:
                OrderClient.pyramid_dict[direction]['freq'] = 0
            OrderClient.pyramid_dict[direction]['orders'].append({
                'orderId':
                    order_reply['data'][
                        'orderId'],
                "symbol": symbol_input,
                'type': type_input,
                'date': datetime.date.today().day
            }
            )
            OrderClient.pyramid_dict[direction]['status'] += 1
            OrderClient.pyramid_dict[direction]['freq'] += 1
            if OrderClient.pyramid_dict[direction]['freq'] >= setting_dict[
                'most_freq']:
                """发送邮件"""
                pass
        print(order_reply, OrderClient.pyramid_dict)
        return {'reply': order_reply, 'pyramid': OrderClient.pyramid_dict}

    @staticmethod
    def close_order(side, orderId_input = None):
        symbol = None
        order_id = None
        direction = 'long' if side == 'BUY' else 'short'
        orders: list = OrderClient.pyramid_dict[direction]['orders']
        if orderId_input:
            for i in range(len(orders)):
                if orders[i]['orderId'] == orderId_input:
                    order_id = orders[i]['orderId']
                    symbol = orders[i]['symbol']
                    del OrderClient.pyramid_dict[direction]['orders'][i]
                    break
        if order_id is None:
            order_id = orders[-1]['orderId']
            symbol = orders[-1]['symbol']
            del OrderClient.pyramid_dict[direction]['orders'][-1]
        OrderClient.client.cancel_order(symbol_input = symbol, orderId = order_id)
        OrderClient.pyramid_dict[direction]['status'] -= 1
        return OrderClient.pyramid_dict[direction]

    @staticmethod
    def get_account_info():
        return OrderClient.client.account_info()

    @staticmethod
    def get_exchange_info(base_filter = 2,
                          side_filter = 'CALL',
                          date_filter = 1,
                          minQty_filter = '0.01'):
        return OrderClient.client.exchange_info(base_filter,
                                                side_filter,
                                                date_filter,
                                                minQty_filter)

    @staticmethod
    def get_account_available(asset = 'USDT'):
        return OrderClient.client.account_available(asset)

    @staticmethod
    def get_proper_symbol(data_array, strike_price):
        return OrderClient.client.proper_symbol(data_array, strike_price)

    @staticmethod
    def get_mark_price(symbol):
        return OrderClient.client.mark_price(symbol)

    @staticmethod
    def all_params_open(params):
        return OrderClient.client.all_params(**params)
