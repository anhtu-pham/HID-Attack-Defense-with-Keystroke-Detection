import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import BaggingClassifier
from utils import *


class CustomMLModel:
    model = None  # to choose the model to use

    def __init__(self, model_name, n_neighbors=None, n_bagging=None):
        self.X = None
        self.y = None
        self.X_train = None
        self.X_eval = None
        self.y_train = None
        self.y_eval = None
        self.model_name = model_name
        self.n_neighbors = n_neighbors
        self.n_bagging = n_bagging

    def train(self, real_filepath, fake_filepath):
        # CONVENTION: 1 IS ATTACK, 0 IS NORMAL

        real_df = pd.read_csv(real_filepath)
        fake_df = pd.read_csv(fake_filepath)

        # real_df = time_difference(real_df)
        # fake_df = time_difference(fake_df)

        # Identify indices of session walls
        real_walls = identify_session(real_df)
        fake_walls = identify_session(fake_df)
        # print(f"REAL WALLS {real_walls}")
        # print(f"FAKE WALLS {fake_walls}")

        group_data = dict()
        group_data["real"] = []
        group_data["fake"] = []

        generate_groups(real_df, walls=real_walls, label='real', dict=group_data)
        generate_groups(fake_df, walls=fake_walls, label='fake', dict=group_data)

        # print(f"GROUP DATA real {len(group_data['real'])}")

        # After generating sessions, we need to calculate the duration 
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
        # print(f"REAL X {real_X}")
        # print(f"FAKE X {fake_X}")

        real_Y = np.zeros(len(real_X))
        fake_Y = np.ones(len(fake_X))

        X = np.concatenate((real_X, fake_X))
        y = np.concatenate((real_Y, fake_Y))

        idx = np.random.permutation(len(X))
        X = X[idx]
        y = y[idx]

        X = X.reshape(-1, 1)
        X_train, X_eval, y_train, y_eval = train_test_split(
            X, y, test_size=0.3, random_state=42, shuffle=False)
        self.X_train = X_train
        self.X_eval = X_eval
        self.y_train = y_train
        self.y_eval = y_eval
        self.X = X
        self.y = y
        
        # Fitting KNN to clusters
        knn_model = KNeighborsClassifier(n_neighbors=self.n_neighbors, algorithm="kd_tree")
        knn_model.fit(X, y)

        if self.model_name == "knn":
            self.model = knn_model
        else:
            # Try with bagging
            bagging_model = BaggingClassifier(estimator=knn_model, n_estimators=self.n_bagging, random_state=42)
            bagging_model.fit(X, y)
            self.model = bagging_model

    def cross_validation(self, k=5):
        scores = cross_val_score(self.model, self.X, self.y, cv=k)
        return np.mean(scores)


    def predict(self, filepath: str):
        pts = predict_preprocess(filepath)
        # print()
        if (pts.size <= 0):
            return False
        result = self.model.predict(pts)
        num_ones = np.count_nonzero(result)
        flag = num_ones >= (len(result) - num_ones)  # if there are more detection of hacking
        # print(f"RESULT {flag}")
        return flag


# Graph purposes:
if __name__=="__main__":
    pd.set_option("display.max_rows", None)  # Show all rows

    test = CustomMLModel("bagging", n_neighbors=5, n_bagging=3)
    test.train("data/real.csv", "data/fake.csv")
    test.predict("data/demo.csv")

    # real_df = pd.read_csv("data/real.csv")
    # real_df = time_difference(real_df)
    # print(real_df[1:100])
    # fake_df = pd.read_csv("data/fake.csv")
    # fake_df = time_difference(fake_df)
    # print(fake_df)

    # knn = CustomMLModel("knn", n_neighbors=5, n_bagging=1)
    # knn.train("data/real.csv", "data/fake.csv")
    # score = knn.cross_validation()
    # print(f"KNN Score: {score}")


    # # Test bagging
    # bagging = CustomMLModel("bagging", n_neighbors=5, n_bagging=3)
    # bagging.train("data/real.csv", "data/fake.csv")
    # score = bagging.cross_validation()
    # print(f"Bagging Score: {score}")

    # baggings = [CustomMLModel("bagging", n_neighbors=5, n_bagging=n) for n in range(1, 15)]
    # scores = []
    # for i, bag in enumerate(baggings):
    #     bag.train("data/real.csv", "data/fake.csv")
    #     score = bag.cross_validation()
    #     scores.append(score)
    # print("Bagging Scores:")
    # print(scores)

    # x_values = np.arange(1, len(scores) + 1)
    # plt.plot(x_values, scores, marker='o', linestyle='-', color='b', label='KNN Scores')
    # plt.xlabel('Number of Estimators in an Ensemble')
    # plt.ylabel('Accuracy')
    # plt.title('Number of Voters vs Accuracy')
    # plt.ylim(0.99, 1.0)  # Example: setting y-axis range from 0.5 to 1.0
    # plt.grid(True)
    # plt.show()

    # knn_list = [CustomMLModel("knn", n_neighbors=n, n_bagging=1) for n in range(1,11)]
    # scores = []
    # for i, knn in enumerate(knn_list):
    #     knn.train("data/real.csv", "data/fake.csv")
    #     score = knn.cross_validation()
    #     scores.append(score)
    # print("KNN Scores:")
    # print(scores)


    # x_values = np.arange(1,8)
    # plt.plot(x_values, scores, marker='o', linestyle='-', color='b', label='KNN Scores')
    # plt.xlabel('k (neighbors)')
    # plt.ylabel('Accuracy')
    # plt.title('KNN Cross-Validation Scores')
    # plt.ylim(0.90, 1.0)  # Example: setting y-axis range from 0.5 to 1.0
    # plt.grid(True)
    # plt.show()