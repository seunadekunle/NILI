import datetime
import random

import pandas as pd
from sklearn.metrics import accuracy_score
import db_setup
from sklearn import model_selection
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import VotingClassifier
import numpy as np
from sklearn.externals import joblib
import time

pd.set_option('display.max_columns', 20)
pd.set_option('expand_frame_repr', True)

model_names = ['dt.joblib', 'knn.joblib']
categoricals = []  # going to one-hot encode categorical variables

dt = None
knn = None


def load_data():
    global df
    global categoricals
    global labels

    db_setup.init_db()

    pd.set_option('display.max_columns', 20)
    pd.set_option('expand_frame_repr', True)

    db_setup.cursor.execute(db_setup.statement)
    df = pd.read_sql(db_setup.statement, con=db_setup.db)

    labels = db_setup.all_labels()

    for col, col_type in df.dtypes.items():
        if col_type == 'O':
            categoricals.append(col)
        else:
            df[col].fillna(0, inplace=True)  # fill NA's with 0 for ints/floats, too generic


def prepare_data():
    global x_train
    global y_train
    global categoricals
    global df

    x_train = df.drop(['id', 'label'], axis=1)
    y_train = df['label']

    # get_dummies effectively creates one-hot encoded variables
    y_train = pd.get_dummies(y_train, columns=categoricals, dummy_na=True)
    y_train.drop(['NaN'], axis=1, errors='ignore')


def get_columns():
    global categoricals

    load_data()
    prepare_data()

    columns = []
    for col in x_train.columns:
        columns.append(col)

    # print(columns)
    return columns


def cross_val(model):
    global x_train
    global y_train

    load_data()
    prepare_data()

    start = time.time()

    validationSize = 0.20
    seed = 4

    x_train, x_validation, y_train, y_validation = model_selection.train_test_split(x_train, y_train,
                                                                                    test_size=validationSize,
                                                                                    random_state=seed)

    # testing options and resetting random seed
    seed = 12
    scoring = 'accuracy'

    # checks accuracy of ML method and outputs accuracy percentage dataset n_splits times
    # scores machine learning model on the dataset
    kfold = model_selection.KFold(n_splits=10, random_state=seed,
                                  shuffle=True)  # n_splits - 1 datasets for training, 1 for validation
    cvResults = model_selection.cross_val_score(model, x_train, y_train, cv=kfold, scoring=scoring)

    print(('Mean: %s  SD: %f') % (cvResults.mean(), cvResults.std()))
    # print(cvResults)

    # fit training data into decision Tree
    model.fit(x_train, y_train)
    print("Trained in " + str(time.time() - start) + " seconds")

    # get predictions from machine learning model
    predictions = model.predict(x_validation)

    # check how accurate the model is using the predictions
    accuracy = accuracy_score(y_validation, predictions, normalize=True)

    labelPrediction = []
    YVal = []

    for i in range(len(predictions)):
        if predictions[i].any():
            labelPrediction.append(labels[decode(predictions[i])])

            # iloc for integer-location based indexing
            YVal.append(
                y_validation.iloc[i][y_validation.iloc[i] == 1].index[0])
    # print(YVal)
    # print(labelPrediction)

    print("Accuracy = " + str(accuracy))
    print("")

    return accuracy

    # confusion matrix
    # confusionMat = confusion_matrix(YVal, labelPrediction)
    # print(confusionMat)

    # TODO: add tuple


def train():
    global dt
    global knn

    load_data()
    prepare_data()
    load_models()

    start = time.time()

    dt.fit(x_train, y_train)
    knn.fit(x_train, y_train)

    print("Trained in " + str(time.time() - start) + " seconds")


def decode(prediction):
    if (not np.any(prediction)):
        result_text = "Electronic Device"
    else:
        result = (np.where(prediction == 1))[0]
        result = result[0]

        #print(result)
        result_text = db_setup.all_labels()[result]

    return result_text


def predict(pred_data):
    global dt
    global knn

    load_models()

    print(pred_data)

    if dt and knn:
        dt_dict = {"prediction": decode(dt.predict(pred_data)[0])}
        knn_dict = {"prediction": decode(knn.predict(pred_data)[0])}

        prediction = ""

        if (dt_dict["prediction"] == knn_dict["prediction"]):
            prediction = dt_dict["prediction"] or knn_dict["prediction"]
        else:
            roll = random.randint(1, 100)

            if roll <= 50:
                prediction = dt_dict["prediction"]
            elif roll >= 51:
                prediction = knn_dict["prediction"]

        print(prediction)
        return prediction
    else:
        return "No prediction"


def load_models():
    global dt
    global knn

    try:
        dt = joblib.load(model_names[0])
        knn = joblib.load(model_names[1])
        print('Models loaded')

    except Exception as e:
        print('No model here')
        print(str(e))
        return


def save_models():
    global dt
    global knn

    if dt or knn:
        joblib.dump(dt, model_names[0])
        joblib.dump(knn, model_names[1])
        print("Models Saved")
    else:
        return "Can't save model"

# TODO: Add Cross Validation
