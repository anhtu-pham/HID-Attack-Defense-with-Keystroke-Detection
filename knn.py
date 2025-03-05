import pandas as pd
import sklearn
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from utils import *

class CustomKNN:
    knn_model = None

    def __init__(self):
        self.train("real.csv", "fake.csv")

    def train(self, real_filepath, fake_filepath):
        # CONVENTION: 1 IS ATTACK, 0 IS NORMAL

        pd.set_option("display.max_rows", None)  # Show all rows

        real_df = pd.read_csv(real_filepath)
        fake_df = pd.read_csv(fake_filepath)
        frames = [real_df, fake_df]

        real_df = time_difference(real_df)
        fake_df = time_difference(fake_df)

        # Filter out extreme values in x 
        # This is not a concern in testing
        real_df = real_df.loc[lambda df: df.Duration < 10, :]

        # Now recompile the Z score, now using median (to compute points)
        real_df = z_score(real_df)
        fake_df = z_score(fake_df)

        # Identify indices of outliers
        real_walls = identify_session(real_df, 0)
        fake_walls = identify_session(fake_df, 0)

        group_data = dict()
        group_data["real"] = []
        group_data["fake"] = []

        generate_groups(real_df, walls=real_walls, label='real', dict=group_data)
        generate_groups(fake_df, walls=fake_walls, label='fake', dict=group_data)

        # print(group_data['real'])
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

        real_Y = np.zeros(len(real_X))
        fake_Y = np.ones(len(fake_X))

        X = np.concatenate((real_X, fake_X))
        y = np.concatenate((real_Y, fake_Y))

        idx = np.random.permutation(len(X))
        X = X[idx]
        y = y[idx]

        X = X.reshape(-1,1)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=1, shuffle=False)

        # Fitting KNN to clusters
        self.knn_model = KNeighborsClassifier(n_neighbors=1)
        self.knn_model.fit(X_train, y_train)
        print("------TEST RESULT:---------")
        print(f"Mean accuracy: {self.knn_model.score(X_test, y_test)} \n")

    def predict(self, filepath: str):
        pts = predict_preprocess(filepath)
        result = self.knn_model.predict(pts)
        num_ones = np.count_nonzero(result)
        flag = num_ones > (len(result) - num_ones)  # if there are more detection of hacking

        if not flag: 
            print("Normal sequence")
        else:
            print("Abnormal behavior. Possible HID attack.")