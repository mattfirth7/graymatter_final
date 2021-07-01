const fs = require('fs');
const AWS = require('aws-sdk');
const express = require('express');
const fileUpload = require('express-fileupload');
const cors = require('cors');
const bodyParser = require('body-parser');
const morgan = require('morgan');
const _ = require('lodash');
var spawn = require('child_process').spawn;
const mysql = require('mysql');
const request = require('request');

// set region if not set (as not set by the SDK by default)
if (!AWS.config.region) {
  AWS.config.update({
    region: 'us-east-1'
  });
}

const s3 = new AWS.S3();
const lambda = new AWS.Lambda();

var con = mysql.createConnection({
	host: process.env.GM_DB_HOSTNAME,
	user: process.env.GM_DB_USERNAME,
	password: process.env.GM_DB_PASSWORD,
	port: 3306,
	database: "graymatter_db"
});

con.connect(function(err) {
	if (err) console.log(err);
});



// Utils
const getModelsList = (callback) => {
	var params = {
		Bucket: 'fake_aws_s3_name',
		Prefix: 'models'
	};
	s3.listObjectsV2(params, function(err, data) {
		if (err) {
			console.log(err, err.stack);
		}
		else  {
			var modelsList = [];
			data.Contents.forEach(item => {
				modelsList.push(item.Key);
			});
			return callback(modelsList);
		}
	});
};

const uploadFile = (csv, location, callback) => {
	const params = {
		Bucket: 'fake_aws_s3_name',
		Key: location + '/' +csv.name,
		Body: fs.createReadStream(csv.tempFilePath)
	};

	s3.upload(params, function (s3Err, data) {
		if (s3Err) {
			console.log("Error", s3Err);
		}

		if (data) {
			console.log("Uploaded in:", data.Location);
			return callback(data.Key);
		}
	});
};

function get_line(filename, line_no, callback) {
	var data = fs.readFileSync(filename.tempFilePath, 'utf8');
	var lines = data.split("\n");

	if (+line_no > lines.length) {
		throw new Error('File end reached without finding line');
	}

	callback(null, lines[+line_no]);
}



//App
const app = express();

app.use(fileUpload({
	useTempFiles : true,
	tempFileDir: './tmp/'
}));

app.use(cors());
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({extended: true}));
app.use(morgan('dev'));

app.set('view engine', 'ejs');
app.set('views', __dirname + '/views');

let port = process.env.PORT;
if (port == null || port == "") {
	port = 3000;
}

app.listen(port, () =>
	console.log(`App is listening on port ${port}.`)
);


// Serve EJS pages
app.get('/', function(req, res) {
	res.render('analyze', {page:'Home', menuId:'analyze'});
});

app.get('/analyze', function(req, res) {
	res.render('analyze', {page:'Analyze', menuId:'analyze'});
});

app.get('/predict', function(req, res) {
	request('https://graymatter.dev/api/models', { json: true }, (err, response, body) =>{
		if (err) console.log(err);

		res.render('predict', {page:'Predict', menuId:'predict', models:body.models});
	});
});


// Api
app.post('/predict-data', async (req, res) => {
	var dataInput = [[]];

	for (var key in req.body) {
		if (req.body.hasOwnProperty(key)) {
			item = req.body[key];
			dataInput[0].push(item);
		}
	}

	modelName = dataInput[0].shift();
	lambda_data = {
		'key1': dataInput,
		'key2': modelName
	};
	var lambda_params = {
		FunctionName: 'fake_aws_lambda_name',
		Payload: JSON.stringify(lambda_data)
	};

	lambda.invoke(lambda_params, function(err, data) {
		if (err) console.log(err);

		else{
			console.log(data);
			prediction = JSON.parse(data['Payload']);
			res.send({
				'prediction': prediction
			});
		}
	});
});


app.get('/api/models/model-name', async (req, res) => {
	console.log('received!');
	console.log(req.query.name);
	var modelName = req.query.name;
	var modelName = modelName.replace('models/', '')
	console.log(modelName);
	con.query(`SELECT input_vars FROM analysis_warehouse WHERE model_name = '${modelName}' LIMIT 1`, function(err, result, fields) {
		if (err) res.send(err);
		console.log(result);
		var featureNames = result[0]['input_vars'].split(',');
		var target = featureNames.pop();
		console.log(featureNames);
		res.render('webapp', {
			page: 'GrayMatter - WebApp',
	  		menuId: '',
	  		featureNames: featureNames,
	  		modelName: req.query.name
	  	});
	});
});


app.get('/api/models', async (req, res) => {
	getModelsList(function(response){
		var modelsList = response;
		res.send({models: modelsList});
	});
});


app.post('/api/models', async (req, res) => {
	if(!req.files) {
		res.sent({
			status: false,
			message: 'No file uploaded'
		});
	} else {
		let csv = req.files.csvfile;
		let dtype = req.body.datatype;

		uploadFile(csv, 'userdata', function(response){
			lambda_data = {
				'key1': response,
				'key2': dtype
			};
			var lambda_params = {
				FunctionName: 'fake_aws_lambda_name',
				Payload: JSON.stringify(lambda_data)
			};
			lambda.invoke(lambda_params, function(err, data) {
				if (err) console.log(err);
				else {
					console.log(data);
					const resultData = JSON.parse(data['Payload']);
					const modelData = JSON.parse(resultData['body']);
					console.log(modelData);
					const modelType = modelData['model_type'];
					const accuracy = modelData['accuracy'];
					const modelName = modelData['model_name'];
					get_line(csv, 0, function(err, line){
						input_vars = line.slice(1);
						con.query(`INSERT INTO analysis_warehouse (dataset_name, dtype, dataset_size, input_vars, model_name, model_type, accuracy) VALUES ('${csv.name}', '${dtype}', '${csv.size}', '${input_vars}', '${modelName}', '${modelType}', '${accuracy}')`, function(err) {
							if (err) res.send(err);
						});
					});

					const model_results = 'Model type: ' + modelType + ' Accuracy: ' + String(accuracy);

					res.render('results', {
						page: 'GrayMatter - Results',
	  					menuId: '',
	  					name: csv.name,
	  					datatype: dtype,
	  					size: csv.size,
	  					results: model_results
	  				});
				}
			});

		});
	}
});

/*
app.post('/prediction', async (req, res) => {
	try {
		if(!req.files) {
			res.send({
				status: false,
				message: 'No file uploaded'
			});
		} else {
			let csv = req.files.csvfile;
			let model = req.body.model;
			let name = csv.name;

			uploadFile(csv, 'predictdata', function(response){
				var data = [response, model];
				var py = spawn('python', ['./app/automl/easy_ai_prediction.py', JSON.stringify(data)]);

				var dataString = '';

				py.stdout.on('data', function(data){
  					dataString += data.toString();
				});

				// Logs any errors that python throws. Easier for debugging
				py.stderr.on('data', (data) => {
					console.log(data.toString());
				});
				py.stdout.on('end', function(){
					res.render('prediction', {
		  				page: 'GrayMatter Research - Predictions',
		  				menuId: '',
		  				results: dataString					
					});
				});
			});

		}
	} catch (err) {
		res.status(500).send(err);
		console.log('catch');
	}

});
*/