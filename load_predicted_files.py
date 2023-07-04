import pandas as pd
import yfinance as yf
import numpy as np


def kaufman_indicator(price: pd.Series, n=6, pow1=2, pow2=10):
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


def get_latest_drop(stock_name):
    last_drop, last_date, lowest_value = None, None, None
    try:
        # creating a dataframe with signal and kama indicator line
        data = yf.download(tickers=f"{stock_name}.NS", period='1y', interval='1d', progress=False)[['Close']]
        stock = pd.DataFrame({
            'price': data['Close'],
            'line': kaufman_indicator(data['Close']),
        })
        stock['signal'] = stock.line.ewm(span=2).mean()

        # max and shift_max are the values from which the drop is calculated
        maximum, shift_max = None, None
        trace_data = stock.signal.dropna()
        returns = trace_data.pct_change() + 1
        return_trace = 1

        # for loop can be removed when we are receiving one data at a time
        for step in range(2, trace_data.shape[0]):
            # if the returns is decreasing then max is none but shift_max is preserved
            if returns.iloc[step] >= 1:
                # if max is not yet defined the first value is stored as maximum
                # else it is checking whether it is maximum or not
                if maximum is None:
                    maximum = trace_data.iloc[step]

                else:
                    if maximum < trace_data.iloc[step]:
                        maximum = trace_data.iloc[step]

                # if max is not yet defined the first max is stored as shift_max
                # suppose the stock was increasing then dropped a little maybe 0.01 and then again started rising
                # then sudden dip and rise is skipped by this shift_max
                # but suppose the max is so low that when it rises, even the 5% rise is less than shift_max then
                # that max is new shift_max. This is handled below
                if shift_max is None and maximum is not None:
                    shift_max = maximum
                else:
                    if shift_max < maximum:
                        shift_max = maximum

                return_trace *= returns.iloc[step]
                if return_trace > 1:
                    drop = (maximum - shift_max) / shift_max
                    if drop < -0.2:
                        # print(f"drop: {drop}",shift_max,trace_data.iloc[step], trace_data.index[step], sep='|')
                        last_date = trace_data.index[step]
                        last_drop = drop
                        shift_max = maximum
                        lowest_value = maximum
            else:
                maximum = None
                return_trace = 1
    except:
        pass
    return last_date, last_drop, lowest_value


def get_data(stock_name):
    raw_data = yf.download(tickers=f"{stock_name}.NS", period='1y', interval='1d')[['Close']]
    stock = pd.DataFrame({
        'price': raw_data['Close'],
        'line': kaufman_indicator(data['Close']),
    })
    stock['signal'] = stock.line.ewm(span=2).mean()
    last_price = stock.iloc[-1].price

    trigger_price = stock.loc[get_latest_drop(stock_name)[0]].price
    counter, counter_returns = 0, []
    returns = stock.pct_change() + 1
    for step in range(stock.shape[0] - 1, -1, -1):
        if returns.iloc[step].price >= 1:
            counter += 1
        else:
            break
    #     counter_returns.append((stock.iloc[step].signal,returns.iloc[step].price))
    return {
        'current_increase': (last_price - trigger_price) / trigger_price,
        'signal_price': trigger_price,
        'last_drop_date': get_latest_drop(stock_name)[0],
        'last_drop': get_latest_drop(stock_name)[1],
        'lowest_value': get_latest_drop(stock_name)[2],
        'counter': counter,
        'last_returns': returns.iloc[-1].price
    }


data_to_convert = {
    "stock": [],
    "increase_after_drop": [],
    "price_at_drop": [],
    "last_drop_date": [],
    "last_drop_value": [],
    "lowest_value": [],
    "increment_counter": [],
    "last_day_returns": []
}
list_of_stocks = pd.read_csv("EQUITY_NSE.csv", header=0)
for stock_symbol in list(list_of_stocks['Symbol']):
    if get_latest_drop(stock_symbol)[0] is None:
        continue
    data = get_data(stock_symbol)
    data_to_convert["stock"].append(stock_symbol)
    data_to_convert["increase_after_drop"].append(data['current_increase'])
    data_to_convert["price_at_drop"].append(data['signal_price'])
    data_to_convert["last_drop_date"].append(data['last_drop_date'])
    data_to_convert["last_drop_value"].append(data['last_drop'])
    data_to_convert["lowest_value"].append(data['lowest_value'])
    data_to_convert["increment_counter"].append(data['counter'])
    data_to_convert["last_day_returns"].append(data['last_returns'])

df = pd.DataFrame(data_to_convert)
df = df[(df['increase_after_drop'] <= 0.05)]
df = df[(df['price_at_drop'] >= 50) & (df['price_at_drop'] < 1000)]
df = df[(df['increment_counter'] <= 2) & (df['increment_counter'] > 0)]
df = df[(df['last_day_returns'] <= 1.08) & (df['last_day_returns'] <= 1.02)]
df.sort_values(by='last_drop_date', ascending=False).to_csv("dash_app/temp/stock_prediction.csv")
