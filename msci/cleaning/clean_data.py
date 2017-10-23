import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from datetime import datetime

COLUMNS_TO_IMPORT = ['mac_address', 'date_time', 'location', 'store_id', 'x', 'y']

shopper_df = pd.read_csv('../data/bag_mus_12-22-2016.csv', usecols=COLUMNS_TO_IMPORT)
shopper_df.date_time = shopper_df.date_time.astype('datetime64[ns]')
p_df = shopper_df[shopper_df['location'] == 'Phoenix Mall']

p = {'name': 'home', 'df': p_df, 'open_time': '09:30:00', 'close_time': '20:00:00'}


def remove_duplicates(shopper_df):
    """
    removes identical signals that are clearly errant duplicates i.e. same time and place for a given mac_id

    :param shopper_df: (pd.DataFrame) the signals of the shoppers
    :return: (pd.DataFrame) the cleaned signals of the shoppers
    """
    shopper_unique_df = shopper_df.drop_duplicates()
    return shopper_unique_df


def remove_outside_hours(shopper_df, open_time, close_time, analysis=False):
    """
    removes mac addresses that are received outside opening hours

    :param shopper_df: (pd.DataFrame) the signals of the shoppers
    :param open_time: ('hh:mm:ss') opening time of mall
    :param close_time: ('hh:mm:ss') closing time of mall
    :return: (pd.DataFrame) the cleaned signals of the shoppers
    """
    date_index_df = shopper_df.copy()
    date_index_df.index = date_index_df.date_time.astype('datetime64[ns]')
    signal_out_of_hours = date_index_df.between_time(close_time, open_time)
    mac_address_out_of_hours = signal_out_of_hours.mac_address.drop_duplicates().tolist()
    shopper_inside_hours_df = shopper_df[~shopper_df.mac_address.isin(mac_address_out_of_hours)]
    shopper_outside_hours_df = shopper_df[shopper_df.mac_address.isin(mac_address_out_of_hours)]
    if analysis:
        return shopper_inside_hours_df, shopper_outside_hours_df
    else:
        return shopper_inside_hours_df


def remove_sparse_data(shopper_df, minimum, analysis=False):
    """
    removes mac_ids that have too few data points to be of use

    :param shopper_df: (pd.DataFrame) the signals of the shoppers
    :param minimum: the threshold for number of data points for a data set to be kept
    :return: (pd.DataFrame) the cleaned signals of the shoppers
    """
    mac_group = shopper_df.groupby('mac_address')
    mac_address_sparse = mac_group.size()[mac_group.size() >= minimum].index.tolist()
    shopper_large_data_df = shopper_df[shopper_df.mac_address.isin(mac_address_sparse)]
    shopper_sparse_data_df = shopper_df[~shopper_df.mac_address.isin(mac_address_sparse)]
    if analysis:
        return shopper_large_data_df, shopper_sparse_data_df
    else:
        return shopper_large_data_df


def remove_unrealistic_speeds(shopper_df, speed, notebook=False, analysis=False):
    """
    removes mac ids that are moving too fast to be pedestrian movement

    :param shopper_df: (pd.DataFrame) the signals of the shoppers
    :param speed: max speed allowed for pedestrian
    :param notebook: allows return of speeds for plotting purposes in notebook
    :return: (pd.DataFrame) the cleaned signals of the shoppers
    """
    shopper_df.date_time = shopper_df.date_time.astype('datetime64[ns]')
    time_sorted = shopper_df.sort_values('date_time')
    mac_group = time_sorted.groupby('mac_address')

    # Remove a single mac address (can't calculate speed)
    macs = mac_group.size()[mac_group.size() > 1].index.tolist()

    mac_too_fast = []
    mac_speeds = []

    for mac in macs:
        mac_dp = mac_group.get_group(mac)
        speeds = _speed_of_group(mac_dp)
        speeds = speeds[speeds < 100000]
        if np.mean(speeds) > speed:
            mac_too_fast.append(mac)
        mac_speeds.append(np.mean(speeds))
    if notebook:
        return mac_speeds
    else:
        shopper_good_speeds_df = shopper_df[~shopper_df.mac_address.isin(mac_too_fast)]
        shopper_wrong_speeds_df = shopper_df[shopper_df.mac_address.isin(mac_too_fast)]
        if analysis:
            return shopper_wrong_speeds_df, shopper_good_speeds_df
        else:
            return shopper_good_speeds_df


def remove_long_gap(shopper_df, max_gap):
    time_sorted = shopper_df.sort_values('date_time')
    mac_group = time_sorted.groupby('mac_address')
    macs = mac_group.mac_address.drop_duplicates().tolist()
    deltas = time_delta(macs, mac_group, plot=False, flat=False)
    exceed = [np.amax(i)>max_gap for i in deltas]
    return exceed


def _speed_of_group(mac_dp):
    """
    computes speeds of mac_ids

    :param mac_dp: reduced dataframe for specific mac_id
    :return: (list) speeds at different times
    """
    x = mac_dp['x'].tolist()
    y = mac_dp['y'].tolist()
    pos = list(zip(x, y))
    times = mac_dp['date_time'].tolist()
    euclideans = np.array([_euclidean_distance(pos[i], pos[i + 1]) for i in range(len(pos) - 1)])
    dt = np.array([_time_difference(times[i], times[i + 1]) for i in range(len(times) - 1)])
    speeds = euclideans / dt
    return speeds


def time_delta(macs, df, plot=True, flat=True):
    df = df.sort_values('date_time')
    mac_group = df.groupby('mac_address')
    td = []
    for mac in macs:
        times = mac_group.get_group(mac).date_time.tolist()
        time_deltas = [_time_difference(times[i],times[i+1]) for i in range(len(times)-1)]
        td.append(time_deltas)
    if plot:
        fig = plt.figure()
        plt.xlabel('Difference in Time Between Readings')
        plt.ylabel('Probability')
        if flat:
            flat_td = [i for sub in td for i in sub]
            plt.hist(flat_td, bins=int(len(flat_td)/3), normed=True)
            fig.show()
            return flat_td
        else:
            for mac in range(len(td)):
                plt.hist(td[mac], bins=200, normed=True)
        fig.show()
    return td


def df_to_csv(df, name, sort=False):
    if sort:
        time_sort = df.sort_values('date_time')
        mac_group = time_sort.groupby('mac_address')
        mac_group.to_csv(path_or_buf='../data/clean_data_' + name + '.csv', columns=COLUMNS_TO_IMPORT, index=False)
    else:
        df.to_csv(path_or_buf='../data/clean_data_' + name + '.csv', columns=COLUMNS_TO_IMPORT, index=False)


def _euclidean_distance(xy1, xy2):
    """
    Returns euclidean distance between points xy1 and xy2

    :param xy1: (tuple) 1st position in (x,y)
    :param xy2: (tuple) 2nd position in (x,y)
    :return: (float) euclidean distance
    """
    return np.sqrt((xy1[0]-xy2[0])**2 + (xy1[1]-xy2[1])**2)


def _time_difference(t0, t1):
    """
    time difference between two timedelta objects
    :param t0: (timedelta object) first timestamp
    :param t1: (timedelta object) second timestamp
    :return: (float) number of seconds elapsed between t0, t1
    """
    td = t1.to_datetime() - t0.to_datetime()
    delta = divmod(td.days * 86400 + td.seconds, 60)
    return delta[0]*60 + delta[1]


def _filter_deviation(means, std):
    data = list(zip(means,std))
    data = [i for i in data if i[1] < 2*i[0]]
    return data


def plot_path(mad, df):
    fig, axes = plt.subplots(nrows=1, ncols=1, figsize=(12, 12))
    for title, group in df[df.mac_address.isin(mad)].groupby('mac_address'):
        group.plot(x='x', y='y', ax=axes, legend=False, linewidth=1)
    fig.show()


def clean(shopper_df, minimum, speed, open_time, close_time):
    """
    cleans the dataframe containing the signals of the shoppers by:
     - removing duplicates
     - removing mac addresses with signals outside of shopping hours
     - removing mac addresses with few signals
     - removing shoppers with unrealistic speeds

    :param shopper_df: (pd.DataFrame) the signals of the shoppers
    :return: (pd.DataFrame) the cleaned signals of the shoppers
    """
    shopper_df = remove_duplicates(shopper_df)
    shopper_df = remove_outside_hours(shopper_df, open_time, close_time)
    shopper_df = remove_sparse_data(shopper_df, minimum)
    shopper_df = remove_unrealistic_speeds(shopper_df, speed)
    return shopper_df


def time_volume_analysis(df):
    fig = plt.figure()
    df.date_time.hist(bins=200)
    plt.xlabel('Time')
    plt.ylabel('Counts')
    fig.show()


def main():
    shopper_df = pd.read_csv('../data/bag_mus_12-22-2016.csv', usecols=COLUMNS_TO_IMPORT)
    shopper_df.date_time = shopper_df.date_time.astype('datetime64[ns]')

    hl_df = shopper_df[shopper_df['location'] == 'Home & Leisure']
    mm_df = shopper_df[shopper_df['location'] == 'Mall of Mauritius']
    p_df = shopper_df[shopper_df['location'] == 'Phoenix Mall']

    minimum = 10
    speed = 3

    locations = [
        {'name': 'home', 'df': hl_df, 'open_time': '09:30:00', 'close_time': '20:00:00'},
        {'name': 'mauritius', 'df': mm_df, 'open_time': '09:30:00', 'close_time': '21:00:00'},
        {'name': 'phoenix', 'df': p_df, 'open_time': '09:30:00', 'close_time': '18:00:00'}
    ]

    for location in locations:
        shopper_cleaned_df = clean(location['df'], minimum, speed, location['open_time'], location['close_time'])
        shopper_cleaned_df.to_csv(
            path_or_buf='../data/clean_data_' + location['name'] + '.csv',
            columns=COLUMNS_TO_IMPORT,
            index=False
        )


#if __name__ == '__main__':
    #main()
