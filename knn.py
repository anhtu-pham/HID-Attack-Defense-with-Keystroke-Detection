import pandas as pd
import sklearn 
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier

# CONVENTION: 1 IS ATTACK, 0 IS NORMAL

pd.set_option("display.max_rows", None)  # Show all rows

real_df = pd.read_csv("real.csv")
fake_df = pd.read_csv("fake.csv")
frames = [real_df, fake_df]

# 1. PREPROCESSING  
# Get the time difference
for i, f in enumerate(frames):
    # print(f["Key"].dtype)
    f["Duration"] = f["Timestamp"].diff()
    f = f.drop(columns=["Key", "Timestamp"]).dropna().reset_index(drop=True)

    mean = f["Duration"].mean()
    std_dev = f["Duration"].std()
    f["Z_score"] = (f["Duration"] - mean) / std_dev
    frames[i] = f

real_df = frames[0]
fake_df = frames[1]

# Filter out extreme values in x 
real_df = real_df.loc[lambda df: df.Z_score < 0, :]

# Now recompile the Z score, now using median (to compute points)
def z_score(df):
    df = df.drop(columns="Z_score").reset_index(drop=True)
    mean = df["Duration"].mean()
    std_dev = df["Duration"].std()
    df["Z_score"] = (df["Duration"] - mean) / std_dev
    return df

real_df = z_score(real_df)
fake_df = z_score(fake_df)

# Identify indices of outliers
real_walls = real_df.index[np.abs(real_df["Z_score"]) > 1]
fake_walls = fake_df.index[(fake_df["Z_score"]) > 0] # 

# print("REAL--------------------")
# print(real_df)
# print("FAKE-------------------")
# print(fake_df)
# print(real_walls)
# print(fake_walls)

group_data = dict()
group_data["real"] = []
group_data["fake"] = []

def generate_groups(df, walls, label):
    floor = 0
    group = []

    #exclusive of last element
    for wall in walls:
        group = df["Z_score"].iloc[floor:wall].values
        floor = wall + 1
        if (len(group) > 1):    # we need 2 or more data to make std > 0
            group_data[label].append(group)

generate_groups(real_df, walls=real_walls, label='real')
generate_groups(fake_df, walls=fake_walls, label='fake')

# Making the data points
real_X = []
fake_X = []

for key, values in group_data.items():
    for v in values:
        pt = np.std(v)
        if key == "real":
            real_X.append(pt)
        elif key == "fake":
            fake_X.append(pt)

real_X = np.array(real_X)
fake_X = np.array(fake_X)

# print(real_X)
# print(fake_X)

real_Y = np.zeros(len(real_X))
fake_Y = np.ones(len(fake_X))

X = np.concatenate((real_X, fake_X))
y = np.concatenate((real_Y, fake_Y))

idx = np.random.permutation(len(X))
X = X[idx]
y = y[idx]

X = X.reshape(-1,1)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.4, random_state=1, shuffle=True)

# print(real_X)
# print(fake_X)

# 2. KNN
# Fitting to clusters
neigh = KNeighborsClassifier(n_neighbors=3)
neigh.fit(X, y)
print(f"Mean accuracy: {neigh.score(X_test, y_test)}")
