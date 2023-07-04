from datetime import datetime
from bson import ObjectId


class Wallet:
    """
        A wallet object is associated with the stock info object till the time it is being tracked.

        A stock info object can be bought and sold several times.
        All the profit will be stored in wallet till the time it is being tracked.

        Once the stock info is destroyed after the tracking time, its link to wallet object is broken.
        So even if the stock info object is destroyed the wallet object remain within the db to track.

        after every sell add the accumulated profit

    """

    def __init__(
            self,
            starting_date: datetime,
            starting_price: float | None,
            stock_symbol: str
    ):
        # if starting date is 07-06-2023 15:30 and current is 10-06-2023 9:50
        # it will be considered not 3 days but 2 days
        # hence the starting date is selected as 07-06-2023 09:10
        self.starting_date = datetime(
            year=starting_date.year,
            month=starting_date.month,
            day=starting_date.day,
            hour=9,
            minute=10
        )
        self.starting_price = starting_price
        self.stock_name = stock_symbol
        self.accumulated_profit = 0
        self.wallet_id = str(ObjectId())

    def has_exceeded_min_return(self) -> bool:
        """
        checks whether the accumulated profit has exceeded the overall profit
        :return: a boolean True or False
        """
        current_date = datetime.now()
        no_of_days = (current_date - self.starting_date).days
        # since start_price*(1+expected_return)**no_of_days = accumulated_profit, so
        actual_return = ((self.accumulated_profit / self.starting_price)**(1/no_of_days)) - 1
        expected_return = ((1+0.005)**no_of_days) - 1
        return actual_return > expected_return


