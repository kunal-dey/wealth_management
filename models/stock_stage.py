from models.costs.delivery_trading_cost import DeliveryTransactionCost
from models.costs.intraday_trading_cost import IntradayTransactionCost
from models.stock_info import StockInfo
from datetime import datetime
from dateutil.rrule import rrule, WEEKLY, MO, TU, WE, TH, FR
from utils.exclude_dates import load_holidays

from logging import Logger

from utils.logger import get_logger

from constants.enums.position_type import PositionType
from constants.enums.product_type import ProductType
from constants.settings import DELIVERY_INITIAL_RETURN, DELIVERY_INCREMENTAL_RETURN , INTRADAY_INITIAL_RETURN

from services.take_position import short

logger: Logger = get_logger(__name__)


class Stage:

    def __init__(
            self,
            buy_price: float,
            position_price: float,
            quantity: int,
            product_type: ProductType,
            position_type: PositionType,
            stock: None | StockInfo = None,
            **kwargs
    ) -> None:
        self.buy_price = buy_price
        self.stock = stock
        self.position_price = position_price
        self.quantity = quantity
        self.product_type = product_type
        self.position_type = position_type

        self.last_price = None
        self.trigger = None

    @property
    def invested_amount(self) -> float:
        """
            amount invested in this stock (transaction cost is not included)
        """
        return self.position_price * abs(self.quantity)

    @property
    def number_of_days(self):
        dtstart, until = self.stock.created_at.date(), datetime.now().date()
        days = rrule(WEEKLY, byweekday=(MO, TU, WE, TH, FR), dtstart=dtstart, until=until).count()
        for day in load_holidays()['dates']:
            if dtstart <= day.date() <= until:
                days -= 1
        return days

    def transaction_cost(self, buying_price, selling_price) -> float:
        logger.info(f"{self.number_of_days}")
        if self.number_of_days > 1:
            return DeliveryTransactionCost(
                buying_price=buying_price,
                selling_price=selling_price,
                quantity=self.quantity
            ).total_tax_and_charges
        else:
            return IntradayTransactionCost(
                buying_price=buying_price,
                selling_price=selling_price,
                quantity=self.quantity
            ).total_tax_and_charges

    @property
    def current_expected_return(self):
        if self.number_of_days > 1:
            return ((1 + DELIVERY_INITIAL_RETURN) ** self.number_of_days) - 1
        else:
            return INTRADAY_INITIAL_RETURN

    @property
    def incremental_return(self):
        return DELIVERY_INCREMENTAL_RETURN

    def set_trigger(self, stock_price: float):
        """
            in case of cumulative position the cost is given by
            cost = sum_i(b_i*q_i)/sum_i(q_i)  + sum_i(f(b_i, q_i, s))/sum_i(q_i)
            where f is an intraday function
            i -> 1 to n.
            n being the number of positions
            b_i is the buying price of the ith position
            q_i is the quantity bought for the ith position

            this can be divided in average buying price(A) + average transaction cost (B)

            Since the cumulative only have LONG as of now so the code for short selling is unchanged
        """
        global logger
        cost = None
        selling_price: float | None = None
        buy_price: float | None = None

        if self.position_type == PositionType.LONG:
            # this handles the A part
            buy_price = self.position_price
            selling_price = stock_price
        else:
            buy_price = stock_price
            selling_price = self.position_price

        # this handles the B part
        tx_cost = self.transaction_cost(buying_price=buy_price, selling_price=selling_price) / self.quantity

        logger.info(f"the total transaction cost for {self.stock.stock_name} is {tx_cost * self.quantity}")

        cost = buy_price + tx_cost

        counter = 1
        earlier_trigger = self.trigger

        logger.info(f"current : {self.current_expected_return}")

        # this section iterates and finds the current trigger achieved
        logger.info(f"cost tracking {cost * (1 + self.current_expected_return + counter * self.incremental_return) - (self.stock.wallet/self.quantity)}")
        while cost * (1 + self.current_expected_return + counter * self.incremental_return) - (self.stock.wallet/self.quantity) < selling_price:
            if self.position_type == PositionType.SHORT:

                self.trigger = selling_price / (cost*(
                        1 + self.current_expected_return + counter * self.incremental_return) - (self.stock.wallet/self.quantity))
            else:
                self.trigger = cost * (1 + self.current_expected_return + counter * self.incremental_return) - (self.stock.wallet/self.quantity)
            counter += 1

        if earlier_trigger is not None:
            if earlier_trigger > self.trigger:
                self.trigger = earlier_trigger

        if self.trigger:
            logger.info(f"current return for {self.stock.stock_name} is  {(self.trigger / (cost - (self.stock.wallet/self.quantity))) - 1}")

    def sell(self):
        short(
            symbol=self.stock.stock_name,
            quantity=self.quantity,
            product_type=self.product_type,
            exchange=self.stock.exchange)
        logger.info(f"Selling {self.stock.stock_name} at {self.last_price} Quantity:{self.quantity}")
        buy_price = self.buy_price
        selling_price = self.stock.latest_price
        tx_cost = self.transaction_cost(buying_price=buy_price, selling_price=selling_price) / self.quantity
        wallet_value = selling_price - (buy_price + tx_cost)
        self.stock.wallet += wallet_value*self.quantity
        logger.info(f"Wallet: {wallet_value}")
        return True

    def breached(self):
        """
            if current price is less than previous trigger then it sells else it updates the trigger
        """
        global logger

        latest_price = self.stock.latest_price  # latest price can be None or float

        if latest_price:
            self.last_price = latest_price

        # if position was long then on achieving the trigger it should sell otherwise it should buy
        # to clear the position
        if (self.position_type == PositionType.LONG) and (self.last_price is not None):
            logger.info(f"{self.stock.stock_name} Earlier trigger:  {self.trigger}, latest price:{self.last_price}")
            if self.trigger is not None:
                # if it hits trigger then square off else reset a new trigger
                if self.last_price < self.trigger/(1+(self.incremental_return/2)):
                    return self.sell()
            else:
                if self.stock.latest_indicator_price:
                    if self.stock.latest_indicator_price < self.position_price:
                        return self.sell()
            self.set_trigger(self.last_price)
            return False
