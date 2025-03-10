import pandas as pd
import numpy as np

def time_difference(f: pd.DataFrame):
    f["Duration"] = f["Timestamp"].diff()
    f = f.drop(columns=["Key", "Timestamp"]).dropna().reset_index(drop=True)

    mean = f["Duration"].mean()
    std_dev = f["Duration"].std()
    f["Z_score"] = (f["Duration"] - mean) / std_dev

    return f

def min_max_scale(arr):
    return (arr - arr.min()) / (arr.max() - arr.min())

def z_score(df):
    df = df.drop(columns="Z_score").reset_index(drop=True)
    mean = df["Duration"].median()
    std_dev = df["Duration"].std()
    df["Duration_Scaled"] = min_max_scale(df["Duration"])
    df["Z_score"] = (df["Duration_Scaled"] - mean) / std_dev
    return df

def identify_session(df: pd.DataFrame, threshold: int):
    # Only accept if the second is larger than 3 secs
    walls = df.index[(df["Z_score"] > threshold)]
    return walls.to_numpy()

def generate_groups(df, walls, label, dict):
    floor = 0
    group = []

    #exclusive of last element
    for wall in walls:
        group = df["Z_score"].iloc[floor:wall].values
        floor = wall + 1
        if (len(group) > 1):    # we need 2 or more data to make std > 0
            dict[label].append(group)

def predict_generate_groups(df, walls):
    floor = 0
    groups = []
    group = []

    if len(walls) == 0:
        groups = df["Z_score"].to_numpy()
        return [groups]
    
    #exclusive of last element
    for wall in walls:
        group = df["Z_score"].iloc[floor:wall].values
        floor = wall + 1
        if (len(group) > 1):    # we need 2 or more data to make std > 0
            groups.append(group)
    
    group = df["Z_score"].iloc[floor:].values
    if (len(group) > 1):
        groups.append(group)

    return groups

def predict_generate_pts(group_data):
    pts = []
    for g in group_data:
        pt = np.std(g)
        pts.append(pt)
    return pts

def predict_preprocess(filepath: str):
    df = pd.read_csv(filepath)
    if df.shape[0] <= 2:
        return None
    df = time_difference(df)
    df = df.loc[lambda df: df.Duration < 10, :]
    df = z_score(df)
    print(f"DF {df}")
    walls = identify_session(df, threshold=0)
    print(f"WALLS {walls}")
    groups = predict_generate_groups(df, walls)
    print(f"groups: {groups}")
    points = predict_generate_pts(groups)
    points = np.array(points)
    print(f"points: {points}")

    points = points.reshape(-1, 1) if len(points) > 1 else points.reshape(1,-1)
    return points