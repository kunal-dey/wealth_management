class DeliveryTransactionCost:
    """
        This class provides the details of all the transaction cost of any delivery charged by zerodha.

        It requires buying price, selling price and quantity.

        Since the calculations were not available, it has been approximated by back calculation.
        A pessimistic approximate is adopted which means the cost calculated
        here is a little bit more than the actual price.

        Various other costs can also be used if required.
        However, to get cost use total_tax and charges.
    """
    brokerage_charges: float
    profit_or_loss: float
    turnover: float
    stt_total: float
    net_transaction_charges: float
    dp_charges: float
    stamp_duty: float
    sebi_charges: float
    gst: float
    total_tax_and_charges: float
    net_pl: float

    def __init__(
            self,
            buying_price: float,
            selling_price: float,
            quantity: int
    ) -> None:
        self.buying_price = buying_price
        self.selling_price = selling_price
        self.quantity = quantity

        # setting the common variables
        self.profit_or_loss = (self.selling_price - self.buying_price) * self.quantity
        self.turnover = (self.buying_price + self.selling_price) * self.quantity

        self.equity_charges()

    def equity_charges(self):
        """
            Calculates each and every charges associated with the stock
        """
        self.brokerage_charges = 0.0
        self.stt_total = (0.1 / 100) * self.turnover
        self.net_transaction_charges = round((0.00345 / 100) * self.turnover, 2)
        self.dp_charges = 15.93 if self.selling_price != 0 else 0
        self.stamp_duty = round((1500 / 10000000) * self.buying_price * self.quantity, 2)
        self.sebi_charges = round(((self.turnover / 10000000) * 10) * 1.18, 2)
        self.gst = 0.18 * (self.brokerage_charges + self.net_transaction_charges + self.sebi_charges / 1.18)
        self.total_tax_and_charges = self.brokerage_charges + self.stt_total + self.net_transaction_charges + self.dp_charges + self.stamp_duty + self.gst + self.sebi_charges
        self.net_pl = self.profit_or_loss - self.total_tax_and_charges
