from models.stock_stage import Stage
from models.stock_info import StockInfo

from constants.enums.position_type import PositionType
from constants.enums.product_type import ProductType
from constants.settings import INTRADAY_INCREMENTAL_RETURN


class Position(Stage):
    COLLECTION_NAME = 'position'

    def __init__(
            self,
            buy_price: float,
            position_price: float,
            quantity: int,
            product_type: ProductType,
            position_type: PositionType,
            symbol: str,
            stock: None | StockInfo = None):
        super().__init__(
            buy_price=buy_price,
            stock=stock,
            position_price=position_price,
            quantity=quantity,
            product_type=product_type,
            position_type=position_type
        )
        self.symbol = symbol

    @property
    def incremental_return(self):
        return INTRADAY_INCREMENTAL_RETURN
