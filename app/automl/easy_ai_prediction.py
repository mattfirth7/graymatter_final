import sys, os, io
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

s3 = boto3.client(service_name = 's3')

def s3_read(filename):
    s3_obj = s3.get_object(Bucket = 'fake_aws_s3_name', Key = filename)
    body = s3_obj['Body']
    return body.read()

def prediction(input_filename, model_name):
    clf = pickle.loads(s3_read(model_name))
    dataset = np.genfromtxt(io.BytesIO(s3_read(input_filename)), delimiter = ',')
    dataset = np.delete(dataset, (0), axis = 0)
    predictions = clf.predict(dataset)
    return predictions


def parse(s):
	return s.replace('[', '').replace(']', '')

def main():
	args = sys.argv

	lines = parse(args[1]).split(',')

	data = lines[0].replace('"', '')
	model = lines[1].replace('"', '')

	predictions = prediction(data, model)
	print(predictions)

if __name__ == '__main__':
	main()

