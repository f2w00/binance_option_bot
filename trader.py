import datetime
import json

from binance_interface.api import EO

# todo 确认账户开通,确认tv参数发送正确
# 打开配置json文件
with open("settings.json", 'r', encoding = 'UTF-8') as f:
    setting_dict = json.load(f)


class BinanceInterface(object):
    client = EO(setting_dict['binance_key'], setting_dict['binance_secret'])

    # account = PM(setting_dict['binance_key'], setting_dict['binance_secret'])

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
    def account_margin():
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
        return order_reply

    @staticmethod
    def close_order(symbol_input, order_id):
        OrderClient.client.cancel_order(symbol_input = symbol_input,
                                        orderId = order_id)
        if order_id in OrderClient.pyramid_dict['short']['orderId']:
            OrderClient.pyramid_dict['short']['status'] -= 1
            OrderClient.pyramid_dict['short']['orderId'].remove(order_id)
        if order_id in OrderClient.pyramid_dict['long']['orderId']:
            OrderClient.pyramid_dict['long']['status'] -= 1
            OrderClient.pyramid_dict['long']['orderId'].remove(order_id)

    @staticmethod
    def get_account_info():
        return OrderClient.client.account_info()

    @staticmethod
    def get_exchange_info():
        return OrderClient.client.exchange_info()

    @staticmethod
    def get_account_margin():
        return OrderClient.client.account_margin()

    @staticmethod
    def get_mark_price(symbol):
        return OrderClient.client.mark_price(symbol)
