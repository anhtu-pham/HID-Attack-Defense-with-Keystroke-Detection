import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.neighbors import KNeighborsClassifier
from utils import *

class CustomKNN:
    knn_model = None

    def __init__(self):
        self.X = None
        self.y = None
        self.X_train = None
        self.X_eval = None
        self.y_train = None
        self.y_eval = None


    def train(self, real_filepath, fake_filepath, n_neighbors):
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
        X_train, X_eval, y_train, y_eval = train_test_split(X, y, test_size=0.3, random_state=42, shuffle=False)
        self.X_train = X_train
        self.X_eval = X_eval
        self.y_train = y_train
        self.y_eval = y_eval
        self.X = X
        self.y = y

        # Fitting KNN to clusters
        self.knn_model = KNeighborsClassifier(n_neighbors=n_neighbors, algorithm='kd_tree')
        self.knn_model.fit(X_train, y_train)
        return self.knn_model

    
    def cross_validation(self, k=5):
        scores = cross_val_score(self.knn_model, self.X, self.y, cv=k)
        return np.mean(scores)


    def predict(self, filepath: str):
        pts = predict_preprocess(filepath)
        result = self.knn_model.predict(pts)
        # print(result)
        num_ones = np.count_nonzero(result)
        flag = num_ones > (len(result) - num_ones)  # if there are more detection of hacking
        print("Normal sequence" if not flag else "Abnormal behavior. Possible HID attack.")


# Demo purpose:
def main():    
    knn = CustomKNN()
    knn.train("data/real.csv", "data/fake.csv", n_neighbors=3)
    knn.predict("data/demo.csv")



# Graph purposes:
# if __name__=="__main__":
#     knn_list = [CustomKNN() for n in range(7)]
#     scores = []
#     for i, knn in enumerate(knn_list):
#         knn.train("data/real.csv", "data/fake.csv", n_neighbors=i+1)
#         score = knn.cross_validation()
#         scores.append(score)

#     x_values = np.arange(1,8)
#     plt.plot(x_values, scores, marker='o', linestyle='-', color='b', label='KNN Scores')
#     plt.xlabel('k (neighbors)')
#     plt.ylabel('Accuracy')
#     plt.title('KNN Cross-Validation Scores')
#     plt.ylim(0.90, 1.0)  # Example: setting y-axis range from 0.5 to 1.0
#     plt.grid(True)
#     plt.show()

