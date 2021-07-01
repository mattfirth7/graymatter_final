import os
import numpy as np
from sklearn import svm
from sklearn import linear_model
import pickle
import easy_validation
import boto3
from botocore.exceptions import ClientError

# need to fix this to use adjusted r2
def __fit_rgr_model(name, rgr, x_train, y_train, x_test, y_test):
    rgr.fit(x_train, y_train)
    model = pickle.dumps(rgr)
    
        
    OUTPUT = 'temp.pickle'
    
    with open(OUTPUT, 'wb') as f:
        f.write(model)
        f.close()
    
    r2 = easy_validation.boostrapping_validation(x_test, y_test)
    os.remove('temp.pickle')
    
    return [name, r2, model]

def ordinary_least_squares(x_train, y_train, x_test, y_test):
    rgr = linear_model.LinearRegression()
    return __fit_rgr_model('ols', rgr, x_train, y_train, x_test, y_test)

def ridge_regr(x_train, y_train, x_test, y_test):
    rgr = linear_model.Ridge()
    return __fit_rgr_model('ridge', rgr, x_train, y_train, x_test, y_test)

def lasso_regr(x_train, y_train, x_test, y_test):
    rgr = linear_model.Lasso()
    return __fit_rgr_model('lasso', rgr, x_train, y_train, x_test, y_test)

def least_angle_regr(x_train, y_train, x_test, y_test):
    rgr = linear_model.Lars()
    return __fit_rgr_model('lars', rgr, x_train, y_train, x_test, y_test)

def bayes_ridge_regr(x_train, y_train, x_test, y_test):
    rgr = linear_model.BayesianRidge()
    return __fit_rgr_model('bayesian_regr', rgr, x_train, y_train, x_test, y_test)

def support_vector_regr(x_train, y_train, x_test, y_test):
    rgr = svm.SVR()
    return __fit_rgr_model('svr', rgr, x_train, y_train, x_test, y_test)

def huber_regr(x_train, y_train, x_test, y_test):
    rgr = linear_model.HuberRegressor()
    return __fit_rgr_model('huber', rgr, x_train, y_train, x_test, y_test)

def easy_regression(input_filename, x_train, y_train, x_test, y_test):
    functions = [ordinary_least_squares, ridge_regr, lasso_regr, 
                 least_angle_regr, bayes_ridge_regr, support_vector_regr,
                 huber_regr]
    results_array = []
    for f in functions:
        results = f(x_train, y_train, x_test, y_test)
        results_array.append(results)
    
    r2_arr = [row[1] for row in results_array]
        
    r2_argmax = np.argmax(r2_arr)
    regr_model = results_array[r2_argmax][0]
    model = results_array[r2_argmax][2]
    name_no_csv = input_filename[:-4]
    name_no_prefix = name_no_csv.replace('userdata/', '')

    OUTPUT = input_filename[:-4] + '_' + regr_model + '_easyai_regression.pickle'
    
    s3 = boto3.resource(service_name = 's3')
    s3.Bucket('fake_aws_s3_name').put_object(Key = 'models/' + OUTPUT, Body = model)
    
    return [regr_model, results_array[r2_argmax][1]]


