from logging import Logger
from time import sleep
from typing import Any
from datetime import datetime

import requests

import pandas as pd
import numpy as np

from constants.global_contexts import kite_context
from constants.settings import set_end_process
from utils.logger import get_logger
from utils.nr_db import connect_to_collection

logger: Logger = get_logger(__name__)


class StockInfo:
    """
        Given a symbol and exchange it holds all the information related to the stock.

        Stock info is retained in db until it doesn't give an expected total return.

        A stock info is created when there is news. Even if there is a news it generally doesn't grow immediately.
        Hence, wallet is created when it is first bought

        last
         maximum will be used when there is no sudden fall and the stock gradually falls till the market is closed
    """

    COLLECTION_NAME = 'stock'

    def __init__(self, symbol: str = None, exchange: str = 'NSE', wallet: float = 0, created_at=datetime.now(),
                 **args) -> None:
        self.symbol = symbol
        self.exchange = exchange
        self.wallet = wallet
        self.stock_name = symbol
        self.created_at = created_at

        self.latest_price = None
        self.latest_indicator_price = None

        self.__result_stock_df: pd.DataFrame | None = None
        self.return_trace = None

        self.high = None
        self.low = None
        self.lowest_indicator = None

        self.first_buy = True

    def json(self):
        """
            This function is used to structure the data so that it can be added in the database
        """
        return {
            "symbol": self.stock_name,
            "exchange": self.exchange,
            "wallet": self.wallet,
            "created_at": self.created_at
        }

    @classmethod
    def to_object(cls, json_data):
        """
            This function is used to convert to object
        """
        return cls(
            symbol=json_data['symbol'],
            exchange=json_data['exchange'],
            wallet=json_data['wallet'],
            created_at=json_data['created_at']
        )

    @property
    def current_price(self):
        """
            returns the current price in the market or else None if the connection interrupts

            tries 4 times
        """
        retries = 0
        while retries < 4:
            try:
                current_price = kite_context.ltp([f"{self.exchange}:{self.stock_name}"])[f"{self.exchange}:{self.stock_name}"]["last_price"]
                if current_price is not None:
                    return float(current_price)
                # response = requests.get(f"http://127.0.0.1:8082/price?symbol={self.stock_name}")
                # return response.json()['data']
            except:
                sleep(1)
            retries += 1
        return None

    def update_price(self):
        """
        This is required to update the latest price.

        It is used to update the csv containing the price for the stock.
        Using it, it updates the latest indicator price which is the last KAMA indicator price.

        The latest KAMA indicator price is used while selling

        :return: None
        """
        current_price = self.current_price
        if current_price == 'ENDED':
            set_end_process(True)
            return
        # if current price is still none in that case older latest price is used if it's not None
        if current_price is not None:
            self.latest_price = current_price
        if self.latest_price is not None:
            self.update_stock_df(self.latest_price)
            actual_price: pd.DataFrame = self.__result_stock_df.copy()
            kuafman_array = self.kaufman_indicator(actual_price['price'])
            actual_price.loc[:, 'line'] = kuafman_array
            actual_price.loc[:, 'signal'] = actual_price.line.ewm(span=10).mean()
            actual_price.dropna(inplace=True)
            actual_price.reset_index(inplace=True)
            if actual_price.shape[0] == 0:
                self.latest_indicator_price = None
            else:
                recent_price = actual_price.signal.iloc[actual_price.shape[0] - 1]
                self.latest_indicator_price = recent_price

            if self.low is None:
                self.low = self.latest_price
            else:
                if self.low > self.latest_price:
                    self.low = self.latest_price

            if self.high is None:
                self.high = self.latest_price
            else:
                if self.high < self.latest_price:
                    self.high = self.latest_price

            if self.lowest_indicator is None:
                self.lowest_indicator = self.latest_indicator_price
            else:
                if self.lowest_indicator > self.latest_indicator_price:
                    self.lowest_indicator = self.latest_indicator_price

    def update_stock_df(self, current_price: float):
        """
        This function updates the csv file which holds the price every 30 sec
        :param current_price:
        :return: None
        """
        try:
            self.__result_stock_df = pd.read_csv(f"temp/{self.stock_name}.csv")
            self.__result_stock_df.drop(self.__result_stock_df.columns[0], axis=1, inplace=True)
        except FileNotFoundError:
            self.__result_stock_df = None
        stock_df = pd.DataFrame({"price": [current_price]})
        if self.__result_stock_df is not None:
            self.__result_stock_df = pd.concat([self.__result_stock_df, stock_df], ignore_index=True)
        else:
            self.__result_stock_df = stock_df
        self.__result_stock_df.to_csv(f"temp/{self.stock_name}.csv")
        self.__result_stock_df = self.__result_stock_df.fillna(method='bfill').fillna(method='ffill')
        self.__result_stock_df.dropna(axis=1, inplace=True)

    @staticmethod
    def kaufman_indicator(price: pd.Series, n=10, pow1=2, pow2=30):
        """
        Given a dataframe, it returns the list of the Kaufman indicator values

        :param price: price dataframe of the stock
        :param n: number of observation
        :param pow1: fastest period
        :param pow2: slowest period
        :return:
        """
        abs_diffx = abs(price - price.shift(1))
        abs_price_change = np.abs(price - price.shift(n))
        vol = abs_diffx.rolling(n).sum()
        er = abs_price_change / vol
        fastest_sc, slowest_sc = 2 / (pow1 + 1), 2 / (pow2 + 1)

        sc = (er * (fastest_sc - slowest_sc) + slowest_sc) ** 2.0

        answer = np.zeros(sc.size)
        n = len(answer)
        first_value = True
        for i in range(n):
            # if volatility is 0 it turns out to be nan so is considered separately
            if vol[i] == 0:
                answer[i] = answer[i - 1] + 1 * (price[i] - answer[i - 1])
            elif sc[i] != sc[i]:
                answer[i] = np.nan
            else:
                if first_value:
                    answer[i] = price[i]
                    first_value = False
                else:
                    answer[i] = answer[i - 1] + sc[i] * (price[i] - answer[i - 1])
        return answer

    def whether_buy(self) -> bool:
        """
        This method will buy whenever it obtains signal.

        It obtains signal in two forms.
        a. If there is a sudden fall or
        b. If there is a gradual decrease in price over time (for this only last maximum is required)
        c. Check whether the return from last days lowest price to today's present price is more than 3%

        a. Conditions for sudden fall
        i it fell by more than 0.5%
        ii reversed the trend

        :return:
        """

        # a. buying for sudden fall
        if False:
            actual_price = self.__result_stock_df.copy()
            actual_price.dropna(inplace=True)
            actual_price.reset_index(inplace=True)
            returns = actual_price.pct_change() + 1
            counter = 0
            for step in range(returns.shape[0] - 1, -1, -1):
                if returns.iloc[step].price >= 1:
                    counter += 1
                else:
                    break
            if counter > 4:
                self.first_buy = False
                return True
        else:
            actual_price = self.__result_stock_df.copy()
            kuafman_array = self.kaufman_indicator(actual_price['price'])
            actual_price.loc[:, 'line'] = kuafman_array
            actual_price.loc[:, 'signal'] = actual_price.line.ewm(span=10).mean()
            actual_price.dropna(inplace=True)
            actual_price.reset_index(inplace=True)
            returns = actual_price.pct_change() + 1

            if actual_price.shape[0] > 1:
                last_step = actual_price.shape[0] - 1
                if returns.signal.iloc[last_step - 1] < 1 <= returns.signal.iloc[last_step] and round(
                        actual_price.signal.iloc[last_step - 1], 2) == round(actual_price.signal.min(), 2):
                    logger.info(f"stock: {self.stock_name}, index: {last_step} ,actual buy")
                    self.return_trace = returns.signal.iloc[last_step]
                if self.return_trace:
                    self.return_trace *= returns.signal.iloc[-1]
                    if self.return_trace > 1.001:
                        logger.info(
                            f"stock: {self.stock_name}, index: {actual_price.shape[0] - 1} ,actual buy")
                        self.return_trace = None
                        return True
        return False

    @classmethod
    async def find_by_name(cls, search_dict):
        """
            This function is used to find a collection by trade symbol
        """
        with connect_to_collection(cls.COLLECTION_NAME) as collection:
            data = await collection.find_one(search_dict)
            return cls.to_object(data) if data else None

    async def save_to_db(self):
        """
            function to insert the object into the database
        """
        with connect_to_collection(self.COLLECTION_NAME) as collection:
            await collection.insert_one(self.json())

    @classmethod
    async def retrieve_all_services(cls):
        """
            If limit or skip is provided then it provides that many element
            Otherwise it provides total list of document
        """
        document_list = []
        with connect_to_collection(cls.COLLECTION_NAME) as collection:
            cursor = collection.find({})
            async for document in cursor:
                document_list.append(cls.to_object(document))
        return document_list

    async def delete_from_db(self, search_dict):
        """
            This function is used to delete the document from collection
        """
        with connect_to_collection(self.COLLECTION_NAME) as collection:
            await collection.delete_one(search_dict)

    @classmethod
    async def update_in_db(cls, search_dict, data: dict[str, Any]):
        """
            This function is used to update fields of banner
        """
        with connect_to_collection(cls.COLLECTION_NAME) as collection:
            await collection.update_one(search_dict, {'$set': data})
