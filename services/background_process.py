from asyncio import sleep
from datetime import datetime
from logging import Logger

from constants.enums.position_type import PositionType
from constants.enums.product_type import ProductType
from constants.settings import END_TIME, SLEEP_INTERVAL, START_TIME, STOP_BUYING_TIME, end_process
from models.account import Account

from models.stock_info import StockInfo
from models.stock_stages.holdings import Holding
from models.stock_stages.positions import Position
from routes.stock_input import chosen_stocks
from services.take_position import long
from utils.logger import get_logger

logger: Logger = get_logger(__name__)


async def background_task():
    """
        all the tasks mentioned here will be running in the background
    """
    global logger

    logger.info("BACKGROUND TASK STARTED")
    current_time = datetime.now()

    account: Account = Account()

    stocks_to_track: dict[str, StockInfo] = {}

    stock_list = await StockInfo.retrieve_all_services()
    logger.info(f"{stock_list}")

    """
        fetch all the stocks already added in stock list
    """
    for stock_obj in stock_list:
        stocks_to_track[stock_obj.symbol] = stock_obj

    holding_list = await Holding.retrieve_all_services()
    logger.info(f"{[holding.json() for holding in holding_list]}")

    for holding_obj in holding_list:
        account.holdings[holding_obj.symbol] = holding_obj
        if holding_obj.symbol in list(stocks_to_track.keys()):
            account.holdings[holding_obj.symbol].stock = stocks_to_track[holding_obj.symbol]

    initial_list_of_holdings = account.holdings.keys()

    while current_time < END_TIME:
        await sleep(SLEEP_INTERVAL)
        current_time = datetime.now()

        try:

            """
                if any new stock is added then it will be added in the stock to track
            """
            for chosen_stock in chosen_stocks():
                if chosen_stock not in list(stocks_to_track.keys()):
                    stocks_to_track[chosen_stock] = StockInfo(chosen_stock, 'NSE')

            """
                update price for all the stocks which are being tracked
            """
            for stock in stocks_to_track.keys():
                stocks_to_track[stock].update_price()

            if end_process():
                break

            """
                if certain criteria is met then buy stocks
            """
            if START_TIME < current_time < STOP_BUYING_TIME:
                account.buy_stocks(stocks_to_track)

            """
                if the trigger for selling is breached in position then sell
            """

            positions_to_delete = []  # this is needed or else it will alter the length during loop

            for position_name in account.positions.keys():
                position: Position = account.positions[position_name]
                if position.breached():
                    logger.info(f" line 89 -->sell {position.stock.stock_name} at {position.stock.latest_price}")
                    positions_to_delete.append(position_name)

            for position_name in positions_to_delete:
                del account.positions[position_name]

            """
                if the trigger for selling is breached in holding then sell
            """

            holdings_to_delete = []  # this is needed or else it will alter the length during loop

            for holding_name in account.holdings.keys():
                holding: Holding = account.holdings[holding_name]

                if holding.breached():
                    logger.info(f" line 89 -->sell {holding.stock.stock_name} at {holding.stock.latest_price}")
                    holdings_to_delete.append(holding_name)

            for holding_name in holdings_to_delete:
                del account.holdings[holding_name]

        except:
            logger.exception("Kite error may have happened")

    """
        At the end of the day decide whether to sell a position, i.e.,
        sell if the latest indicator price is greater than the buying price
    """

    for stock_key in stocks_to_track.keys():
        """
            At the end of the day decide whether to buy a stock if it is falling
        """
        if stock_key not in account.positions.keys():
            stock = stocks_to_track[stock_key]
            close, high, low = stock.latest_price, stock.high, stock.low
            if close < high*(1-0.01) and close < low*(1+0.005):
                if long(
                    symbol=stocks_to_track[stock_key].symbol,
                    quantity=int(5000 / stocks_to_track[stock_key].latest_indicator_price),
                    product_type=ProductType.DELIVERY,
                    exchange=stocks_to_track[stock_key].exchange
                ):
                    account.positions[stock_key] = Position(
                        buy_price=stocks_to_track[stock_key].latest_price,
                        stock=stocks_to_track[stock_key],
                        position_type=PositionType.LONG,
                        position_price=stocks_to_track[stock_key].latest_indicator_price,
                        quantity=int(5000 / stocks_to_track[stock_key].latest_indicator_price),
                        product_type=ProductType.DELIVERY,
                        symbol=stock_key
                    )

        """
            if the remaining stock to track is already available update it or else add a new record in db
        """
        stock_model = await stocks_to_track[stock_key].find_by_name({'symbol': stock_key})
        if stock_model is None:
            await stocks_to_track[stock_key].save_to_db()
        else:
            await stocks_to_track[stock_key].update_in_db(
                search_dict={'symbol': stock_key},
                data={'wallet': stocks_to_track[stock_key].wallet}
            )

    for position_key in account.positions:
        position = account.positions[position_key]
        account.holdings[position_key] = Holding(
            buy_price=position.buy_price,
            position_price=position.position_price,
            quantity=position.quantity,
            product_type=position.product_type,
            position_type=position.position_type,
            symbol=position.symbol,
            stock=position.stock
        )

    for holding_key in account.holdings.keys():
        holding_model = await account.holdings[holding_key].find_by_name({'symbol': holding_key})
        if holding_model is None:
            await account.holdings[holding_key].save_to_db()
        else:
            await account.holdings[holding_key].update_in_db(
                search_dict={'symbol': holding_key},
                data=account.holdings[holding_key].json()
            )

    for holding_key in initial_list_of_holdings:
        if holding_key not in list(account.holdings.keys()):
            await account.holdings[holding_key].delete_from_db(search_dict={'symbol': holding_key})

    logger.info("TASK ENDED")
