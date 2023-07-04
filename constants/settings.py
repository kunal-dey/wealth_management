from datetime import datetime

__current_time = datetime.now()
START_TIME = datetime(__current_time.year, __current_time.month, __current_time.day, 9, 15, 0)
END_TIME = datetime(__current_time.year, __current_time.month, __current_time.day, 15, 13)
STOP_BUYING_TIME = datetime(__current_time.year, __current_time.month, __current_time.day, 15, 10, 0)

SLEEP_INTERVAL: float = 45

# expected returns are set in this section
DELIVERY_INITIAL_RETURN = 0.008
DELIVERY_INCREMENTAL_RETURN = 0.006
DRAWDOWN_ALLOWED = 0.03

INTRADAY_INITIAL_RETURN = 0.008
INTRADAY_INCREMENTAL_RETURN = 0.008

END_PROCESS = False


def end_process():
    """
        function is used to get list of selected stocks
    :return:
    """
    global END_PROCESS
    return END_PROCESS


def set_end_process(value):
    global END_PROCESS
    END_PROCESS = value


