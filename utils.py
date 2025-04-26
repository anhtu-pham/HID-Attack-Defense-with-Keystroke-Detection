import pandas as pd
import numpy as np

def identify_session(df: pd.DataFrame):
    walls = df.index[(df["Timestamp"]== -1)]
    return walls.to_numpy()

def generate_groups(df, walls, label, dict):
    floor = 0
    walls = np.append(walls, len(df))

    #exclusive of last element
    for wall in walls:
        group = df["Timestamp"].iloc[floor+1:wall].values
        group = np.diff(group)
        floor = wall + 1
        if (len(group) > 1):    # we need 2 or more data to make std > 0
            groups = split_to_smaller_groups(group, 20)
            for group in groups:
                dict[label].append(group)

def predict_generate_groups(df, walls):
    floor = 0
    all_groups = []
    walls = np.append(walls, len(df))
    #exclusive of last element
    for wall in walls:
        group = df["Timestamp"].iloc[floor+1:wall].values
        group = np.diff(group)
        floor = wall + 1
        if (len(group) > 1):    # we need 2 or more data to make std > 0
            groups = split_to_smaller_groups(group, 20)
            for group in groups:
                all_groups.append(group)

    return all_groups

def split_to_smaller_groups(group, size = 20):
    groups = []
    for i in range(0, len(group), size):
        groups.append(group[i:i+size])
    # If the last group is smaller than min_size, we need to merge it with the previous group
    if len(groups) > 1 and len(groups[-1]) < size / 2:
        groups[-2] = np.concatenate((groups[-2], groups[-1]))
        groups.pop()

    # If the session is smaller than the size, we don't need to split it
    if len(groups) == 1 and len(groups[0]) < size:
        return groups

    return groups


def predict_generate_pts(group_data):
    pts = []
    for g in group_data:
        pt = np.std(g)
        pts.append(pt)
    return pts

def predict_preprocess(filepath: str):
    df = pd.read_csv(filepath)

    # Check if the file is empty
    if df.shape[0] <= 2:
        return None
    
    # Locate the sessions
    walls = identify_session(df)
    # print(f"WALLS {walls}")

    groups = predict_generate_groups(df, walls)
    # print(f"groups: {groups}")
    points = predict_generate_pts(groups)
    points = np.array(points)
    # print(f"points: {points}")

    points = points.reshape(-1, 1) if len(points) > 1 else points.reshape(1,-1)
    return points