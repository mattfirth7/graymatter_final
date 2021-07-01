import os
import numpy as np
from sklearn import preprocessing, neighbors, svm
from sklearn.neighbors import KNeighborsClassifier
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.gaussian_process.kernels import RBF
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.discriminant_analysis import QuadraticDiscriminantAnalysis
import pickle
import easy_validation
import boto3
from botocore.exceptions import ClientError


def __fit_clf_model(name, clf, x_train, y_train, x_test, y_test):
    clf.fit(x_train, y_train)
    model = pickle.dumps(clf)
    
    OUTPUT = 'temp.pickle'
    
    with open(OUTPUT, 'wb') as f:
        f.write(model)
        f.close()
    
    accuracy = easy_validation.boostrapping_validation(x_test, y_test)
    os.remove('temp.pickle')
    return [name, accuracy, model]



#still need to add optimization over hyperparameters
def k_nearest(x_train, y_train, x_test, y_test):
    clf = KNeighborsClassifier(n_neighbors = 3)
    return __fit_clf_model('k_nearest', clf, x_train, y_train, x_test, y_test)

# poly kernel is not working so it has been removed
def support_vector_machine(x_train, y_train, x_test, y_test):
    model_arr = []
    accuracy_arr = []
    for kernel in ('linear', 'rbf'):
        clf = svm.SVC(kernel = kernel, gamma = 2)
        model_info = __fit_clf_model(kernel + '_svm', clf, x_train, y_train, x_test, y_test)
        model_arr.append(model_info)
        accuracy_arr.append(model_info[1])
        
    accuracy_argmax = np.argmax(accuracy_arr)
    return model_arr[accuracy_argmax]

#still need to add optimization over hyperparameters
def gaussian_process_classifier(x_train, y_train, x_test, y_test):
    kernel = 1.0 * RBF(1.0)
    clf = GaussianProcessClassifier(kernel = kernel, random_state = 0)
    return __fit_clf_model('gaussian_process', clf, x_train, y_train, x_test, y_test)

#still need to add optimization over hyperparamters
def decision_tree_classifier(x_train, y_train, x_test, y_test):
    clf = DecisionTreeClassifier(random_state = 0)
    return __fit_clf_model('decision_tree', clf, x_train, y_train, x_test, y_test)

#still need to add optimization over hyperparameters
def random_forest_classifier(x_train, y_train, x_test, y_test):
    clf = RandomForestClassifier(max_depth = 2, random_state = 0)
    return __fit_clf_model('random_forest', clf, x_train, y_train, x_test, y_test)

#still need to add optimization over hyperparameters
def adaboost_classifier(x_train, y_train, x_test, y_test):
    clf = AdaBoostClassifier(n_estimators = 100, random_state = 0)
    return __fit_clf_model('adaboost', clf, x_train, y_train, x_test, y_test)

def native_bayes(x_train, y_train, x_test, y_test):
    clf = GaussianNB()
    return __fit_clf_model('native_bayes', clf, x_train, y_train, x_test, y_test)

def quadratic_discriminant(x_train, y_train, x_test, y_test):
    clf = QuadraticDiscriminantAnalysis()
    return __fit_clf_model('quadratic_discriminant', clf, x_train, y_train, x_test, y_test)

#Do I want to add something like rerunning classifiers with the highest accuracies
#to get a better estimate of mean accuracy?
def easy_classification(input_filename, x_train, y_train, x_test, y_test):
    functions = [k_nearest, support_vector_machine, decision_tree_classifier, 
                 random_forest_classifier, adaboost_classifier, native_bayes]
    results_array = []
    for f in functions:
        results = f(x_train, y_train, x_test, y_test)
        results_array.append(results)
    #quadratic discriminant analysis is not currently working
    #results_array.append(quadratic_discriminant(x_train, y_train, x_test, y_test))
    
    accuracies_arr = [row[1] for row in results_array]
        
    accuracy_argmax = np.argmax(accuracies_arr)
    classifier = results_array[accuracy_argmax][0]
    model = results_array[accuracy_argmax][2]

    name_no_csv = input_filename[:-4]
    name_no_prefix = name_no_csv.replace('userdata/', '')

    OUTPUT = name_no_prefix + '_' + classifier + '_easyai_classifier.pickle'

    s3 = boto3.resource(service_name = 's3')
    s3.Bucket('fake_aws_s3_name').put_object(Key = 'models/' + OUTPUT, Body = model)

    return [classifier, results_array[accuracy_argmax][1]]