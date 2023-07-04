from typing import Any

from models.stock_stage import Stage
from models.stock_info import StockInfo

from constants.enums.position_type import PositionType
from constants.enums.product_type import ProductType

from constants.settings import DELIVERY_INCREMENTAL_RETURN
from utils.nr_db import connect_to_collection


class Holding(Stage):
    COLLECTION_NAME = 'holding'

    def __init__(
            self,
            buy_price: float,
            position_price: float,
            quantity: int,
            product_type: ProductType,
            position_type: PositionType,
            symbol: str,
            stock: None | StockInfo = None,
            **kwargs
    ):
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
        return DELIVERY_INCREMENTAL_RETURN

    def json(self):
        """
            This function is used to structure the data so that it can be added in the database
        """
        return {
            "buy_price": self.buy_price,
            "position_price": self.position_price,
            "quantity": self.quantity,
            "product_type": self.product_type.value,
            "position_type": self.position_type.value,
            "symbol": self.symbol
        }

    @classmethod
    def to_object(cls, json_data):
        """
            This function is used to convert to object
        """
        return cls(
            buy_price=json_data['buy_price'],
            position_price=json_data['position_price'],
            quantity=json_data['quantity'],
            product_type=ProductType(json_data['product_type']),
            position_type=PositionType(json_data['position_type']),
            symbol=json_data['symbol']
        )

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

