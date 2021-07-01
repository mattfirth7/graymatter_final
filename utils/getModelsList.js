const AWS = require('aws-sdk');


const getModelsList = (callback) => {
	const s3 = new AWS.S3();
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