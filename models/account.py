from logging import Logger

from constants.enums.position_type import PositionType
from constants.enums.product_type import ProductType
from models.stock_info import StockInfo
from models.stock_stages.holdings import Holding
from models.stock_stages.positions import Position
from services.take_position import long
from utils.logger import get_logger

logger: Logger = get_logger(__name__)


class Account:

    def __init__(self) -> None:
        self.positions: dict[str, Position] = {}
        self.holdings: dict[str, Holding] = {}

    def buy_stocks(self, stock_to_track: dict[str, StockInfo]):
        """
        if it satisfies all the buying criteria then it buys the stock
        :param stock_to_track:
        :return: None
        """

        for stock_key in stock_to_track:
            if stock_key not in self.positions.keys() and stock_to_track[stock_key].whether_buy() and stock_key not in self.holdings.keys():
                if long(
                    symbol=stock_to_track[stock_key].symbol,
                    quantity=int(5000 / stock_to_track[stock_key].latest_indicator_price),
                    product_type=ProductType.DELIVERY,
                    exchange=stock_to_track[stock_key].exchange
                ):
                    logger.info(f"{stock_to_track[stock_key].stock_name} has been bought @ {stock_to_track[stock_key].latest_price}.")
                    self.positions[stock_key] = Position(
                        buy_price=stock_to_track[stock_key].latest_price,
                        stock=stock_to_track[stock_key],
                        position_type=PositionType.LONG,
                        position_price=stock_to_track[stock_key].latest_indicator_price,
                        quantity=int(5000 / stock_to_track[stock_key].latest_indicator_price),
                        product_type=ProductType.DELIVERY,
                        symbol=stock_key
                    )
