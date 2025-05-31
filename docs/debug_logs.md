Back to top
Log events  

Actions
Start tailing
Create metric filter
You can use the filter bar below to search for and match terms, phrases, or values in your log events. Learn more about filter patterns 

1m
1h

Clear

Local timezone
Display

Timestamp
	
Message

Timestamp
	
Message

No older events at this moment. 
Retry
2025-05-30T21:58:39.793-06:00
INIT_START Runtime Version: nodejs:18.v71	Runtime Version ARN: arn:aws:lambda:us-west-2::runtime:bcd7c0a83c1c6bc9b4982403f8200084d0db1fe61d7c4d3215979c11bb00d650
INIT_START Runtime Version: nodejs:18.v71 Runtime Version ARN: arn:aws:lambda:us-west-2::runtime:bcd7c0a83c1c6bc9b4982403f8200084d0db1fe61d7c4d3215979c11bb00d650
2025-05-30T21:58:40.335-06:00
START RequestId: 0e7648a4-caea-49e5-8b76-e5e804bc4d60 Version: $LATEST
START RequestId: 0e7648a4-caea-49e5-8b76-e5e804bc4d60 Version: $LATEST
2025-05-30T21:58:40.474-06:00
2025-05-31T03:58:40.474Z	0e7648a4-caea-49e5-8b76-e5e804bc4d60	INFO	Event received: 
{
    "resource": "/start-multipart-upload",
    "path": "/start-multipart-upload",
    "httpMethod": "POST",
    "headers": {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "CloudFront-Forwarded-Proto": "https",
        "CloudFront-Is-Desktop-Viewer": "true",
        "CloudFront-Is-Mobile-Viewer": "false",
        "CloudFront-Is-SmartTV-Viewer": "false",
        "CloudFront-Is-Tablet-Viewer": "false",
        "CloudFront-Viewer-ASN": "13335",
        "CloudFront-Viewer-Country": "US",
        "content-type": "application/json",
        "Host": "o7d0i4to5a.execute-api.us-west-2.amazonaws.com",
        "origin": "https://dev.hansentour.com",
        "priority": "u=3, i",
        "Referer": "https://dev.hansentour.com/",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15",
        "Via": "2.0 94d9d221defc9832eeda31acd3f6f552.cloudfront.net (CloudFront)",
        "X-Amz-Cf-Id": "7nKg_NcgI-9ecxkb_c7ItztDnXxRjKcKoyqzKSs8GeEY7f685xp2vQ==",
        "X-Amzn-Trace-Id": "Root=1-683a7e6f-140f72eb71ce2334603453b4",
        "X-Forwarded-For": "104.28.48.213, 3.172.27.14",
        "X-Forwarded-Port": "443",
        "X-Forwarded-Proto": "https"
    },
    "multiValueHeaders": {
        "Accept": [
            "*/*"
        ],
        "Accept-Encoding": [
            "gzip, deflate, br"
        ],
        "Accept-Language": [
            "en-US,en;q=0.9"
        ],
        "CloudFront-Forwarded-Proto": [
            "https"
        ],
        "CloudFront-Is-Desktop-Viewer": [
            "true"
        ],
        "CloudFront-Is-Mobile-Viewer": [
            "false"
        ],
        "CloudFront-Is-SmartTV-Viewer": [
            "false"
        ],
        "CloudFront-Is-Tablet-Viewer": [
            "false"
        ],
        "CloudFront-Viewer-ASN": [
            "13335"
        ],
        "CloudFront-Viewer-Country": [
            "US"
        ],
        "content-type": [
            "application/json"
        ],
        "Host": [
            "o7d0i4to5a.execute-api.us-west-2.amazonaws.com"
        ],
        "origin": [
            "https://dev.hansentour.com"
        ],
        "priority": [
            "u=3, i"
        ],
        "Referer": [
            "https://dev.hansentour.com/"
        ],
        "sec-fetch-dest": [
            "empty"
        ],
        "sec-fetch-mode": [
            "cors"
        ],
        "sec-fetch-site": [
            "cross-site"
        ],
        "User-Agent": [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15"
        ],
        "Via": [
            "2.0 94d9d221defc9832eeda31acd3f6f552.cloudfront.net (CloudFront)"
        ],
        "X-Amz-Cf-Id": [
            "7nKg_NcgI-9ecxkb_c7ItztDnXxRjKcKoyqzKSs8GeEY7f685xp2vQ=="
        ],
        "X-Amzn-Trace-Id": [
            "Root=1-683a7e6f-140f72eb71ce2334603453b4"
        ],
        "X-Forwarded-For": [
            "104.28.48.213, 3.172.27.14"
        ],
        "X-Forwarded-Port": [
            "443"
        ],
        "X-Forwarded-Proto": [
            "https"
        ]
    },
    "queryStringParameters": null,
    "multiValueQueryStringParameters": null,
    "pathParameters": null,
    "stageVariables": null,
    "requestContext": {
        "resourceId": "3gaqex",
        "resourcePath": "/start-multipart-upload",
        "httpMethod": "POST",
        "extendedRequestId": "LaixfFENPHcERVw=",
        "requestTime": "31/May/2025:03:58:39 +0000",
        "path": "/prod/start-multipart-upload",
        "accountId": "975050048887",
        "protocol": "HTTP/1.1",
        "stage": "prod",
        "domainPrefix": "o7d0i4to5a",
        "requestTimeEpoch": 1748663919587,
        "requestId": "f38e0f68-868e-40fe-bf81-915446983ad3",
        "identity": {
            "cognitoIdentityPoolId": null,
            "accountId": null,
            "cognitoIdentityId": null,
            "caller": null,
            "sourceIp": "104.28.48.213",
            "principalOrgId": null,
            "accessKey": null,
            "cognitoAuthenticationType": null,
            "cognitoAuthenticationProvider": null,
            "userArn": null,
            "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15",
            "user": null
        },
        "domainName": "o7d0i4to5a.execute-api.us-west-2.amazonaws.com",
        "deploymentId": "83bgxq",
        "apiId": "o7d0i4to5a"
    },
    "body": "{\"propertyTitle\":\"DummyTester\",\"addressOfProperty\":\"ur mom\",\"listingDescription\":\"yooooaooa\",\"email\":\"gbhbyu@gmail.com\",\"optionalNotes\":\"oogabooga\",\"fileName\":\"Archive.zip\",\"fileType\":\"application/zip\"}",
    "isBase64Encoded": false
}

2025-05-31T03:58:40.474Z 0e7648a4-caea-49e5-8b76-e5e804bc4d60 INFO Event received: {"resource":"/start-multipart-upload","path":"/start-multipart-upload","httpMethod":"POST","headers":{"Accept":"*/*","Accept-Encoding":"gzip, deflate, br","Accept-Language":"en-US,en;q=0.9","CloudFront-Forwarded-Proto":"https","CloudFront-Is-Desktop-Viewer":"true","CloudFront-Is-Mobile-Viewer":"false","CloudFront-Is-SmartTV-Viewer":"false","CloudFront-Is-Tablet-Viewer":"false","CloudFront-Viewer-ASN":"13335","CloudFront-Viewer-Country":"US","content-type":"application/json","Host":"o7d0i4to5a.execute-api.us-west-2.amazonaws.com","origin":"https://dev.hansentour.com","priority":"u=3, i","Referer":"https://dev.hansentour.com/","sec-fetch-dest":"empty","sec-fetch-mode":"cors","sec-fetch-site":"cross-site","User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15","Via":"2.0 94d9d221defc9832eeda31acd3f6f552.cloudfront.net (CloudFront)","X-Amz-Cf-Id":"7nKg_NcgI-9ecxkb_c7ItztDnXxRjKcKoyqzKSs8GeEY7f685xp2vQ==","X-Amzn-Trace-Id":"Root=1-683a7e6f-140f72eb71ce2334603453b4","X-Forwarded-For":"104.28.48.213, 3.172.27.14","X-Forwarded-Port":"443","X-Forwarded-Proto":"https"},"multiValueHeaders":{"Accept":["*/*"],"Accept-Encoding":["gzip, deflate, br"],"Accept-Language":["en-US,en;q=0.9"],"CloudFront-Forwarded-Proto":["https"],"CloudFront-Is-Desktop-Viewer":["true"],"CloudFront-Is-Mobile-Viewer":["false"],"CloudFront-Is-SmartTV-Viewer":["false"],"CloudFront-Is-Tablet-Viewer":["false"],"CloudFront-Viewer-ASN":["13335"],"CloudFront-Viewer-Country":["US"],"content-type":["application/json"],"Host":["o7d0i4to5a.execute-api.us-west-2.amazonaws.com"],"origin":["https://dev.hansentour.com"],"priority":["u=3, i"],"Referer":["https://dev.hansentour.com/"],"sec-fetch-dest":["empty"],"sec-fetch-mode":["cors"],"sec-fetch-site":["cross-site"],"User-Agent":["Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15"],"Via":["2.0 94d9d221defc9832eeda31acd3f6f552.cloudfront.net (CloudFront)"],"X-Amz-Cf-Id":["7nKg_NcgI-9ecxkb_c7ItztDnXxRjKcKoyqzKSs8GeEY7f685xp2vQ=="],"X-Amzn-Trace-Id":["Root=1-683a7e6f-140f72eb71ce2334603453b4"],"X-Forwarded-For":["104.28.48.213, 3.172.27.14"],"X-Forwarded-Port":["443"],"X-Forwarded-Proto":["https"]},"queryStringParameters":null,"multiValueQueryStringParameters":null,"pathParameters":null,"stageVariables":null,"requestContext":{"resourceId":"3gaqex","resourcePath":"/start-multipart-upload","httpMethod":"POST","extendedRequestId":"LaixfFENPHcERVw=","requestTime":"31/May/2025:03:58:39 +0000","path":"/prod/start-multipart-upload","accountId":"975050048887","protocol":"HTTP/1.1","stage":"prod","domainPrefix":"o7d0i4to5a","requestTimeEpoch":1748663919587,"requestId":"f38e0f68-868e-40fe-bf81-915446983ad3","identity":{"cognitoIdentityPoolId":null,"accountId":null,"cognitoIdentityId":null,"caller":null,"sourceIp":"104.28.48.213","principalOrgId":null,"accessKey":null,"cognitoAuthenticationType":null,"cognitoAuthenticationProvider":null,"userArn":null,"userAgent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15","user":null},"domainName":"o7d0i4to5a.execute-api.us-west-2.amazonaws.com","deploymentId":"83bgxq","apiId":"o7d0i4to5a"},"body":"{\"propertyTitle\":\"DummyTester\",\"addressOfProperty\":\"ur mom\",\"listingDescription\":\"yooooaooa\",\"email\":\"gbhbyu@gmail.com\",\"optionalNotes\":\"oogabooga\",\"fileName\":\"Archive.zip\",\"fileType\":\"application/zip\"}","isBase64Encoded":false}
2025-05-30T21:58:40.474-06:00
2025-05-31T03:58:40.474Z	0e7648a4-caea-49e5-8b76-e5e804bc4d60	INFO	Path: /start-multipart-upload
2025-05-31T03:58:40.474Z 0e7648a4-caea-49e5-8b76-e5e804bc4d60 INFO Path: /start-multipart-upload
2025-05-30T21:58:41.453-06:00
2025-05-31T03:58:41.453Z	0e7648a4-caea-49e5-8b76-e5e804bc4d60	INFO	Multipart upload initiated: {
  '$metadata': {
    httpStatusCode: 200,
    requestId: 'BJRMT2TM68PXXKVX',
    extendedRequestId: 'vbEyuVM3h3mnLhJ1jugy6vYUseficn28on99P6hJmWC0o1R4ttsyvbVXiJdM/hCp11Uvjq2xjm0=',
    cfId: undefined,
    attempts: 1,
    totalRetryDelay: 0
  },
  ServerSideEncryption: 'AES256',
  Bucket: 'spaceport-uploads',
  Key: '1748663920512-5nvr6q-Archive.zip',
  UploadId: 'LPHQdRuwSSissIM1GmDiB_L_Eoun68VuNI_VF02m1g_1eWoczBd3ErEkYdg4l8ljRZhE34TyVrCwzgVHi1Dn7MDl.4SXArRWKnAMrvG9Rzj6kdQ1HCb3WiPtdAG3LG_vYFZsNg9.xEd08dRQH2.vcLNr0Ilp8QitH04icxURJLk-'
}
2025-05-31T03:58:41.453Z 0e7648a4-caea-49e5-8b76-e5e804bc4d60 INFO Multipart upload initiated: { '$metadata': { httpStatusCode: 200, requestId: 'BJRMT2TM68PXXKVX', extendedRequestId: 'vbEyuVM3h3mnLhJ1jugy6vYUseficn28on99P6hJmWC0o1R4ttsyvbVXiJdM/hCp11Uvjq2xjm0=', cfId: undefined, attempts: 1, totalRetryDelay: 0 }, ServerSideEncryption: 'AES256', Bucket: 'spaceport-uploads', Key: '1748663920512-5nvr6q-Archive.zip', UploadId: 'LPHQdRuwSSissIM1GmDiB_L_Eoun68VuNI_VF02m1g_1eWoczBd3ErEkYdg4l8ljRZhE34TyVrCwzgVHi1Dn7MDl.4SXArRWKnAMrvG9Rzj6kdQ1HCb3WiPtdAG3LG_vYFZsNg9.xEd08dRQH2.vcLNr0Ilp8QitH04icxURJLk-' }
2025-05-30T21:58:41.514-06:00
END RequestId: 0e7648a4-caea-49e5-8b76-e5e804bc4d60
END RequestId: 0e7648a4-caea-49e5-8b76-e5e804bc4d60
2025-05-30T21:58:41.514-06:00
REPORT RequestId: 0e7648a4-caea-49e5-8b76-e5e804bc4d60	Duration: 1177.96 ms	Billed Duration: 1178 ms	Memory Size: 128 MB	Max Memory Used: 91 MB	Init Duration: 539.31 ms	
REPORT RequestId: 0e7648a4-caea-49e5-8b76-e5e804bc4d60 Duration: 1177.96 ms Billed Duration: 1178 ms Memory Size: 128 MB Max Memory Used: 91 MB Init Duration: 539.31 ms
2025-05-30T21:58:41.758-06:00
START RequestId: 6024a5ff-0783-4df3-aaf2-e2af855ec92e Version: $LATEST
START RequestId: 6024a5ff-0783-4df3-aaf2-e2af855ec92e Version: $LATEST
2025-05-30T21:58:41.759-06:00
2025-05-31T03:58:41.759Z	6024a5ff-0783-4df3-aaf2-e2af855ec92e	INFO	Event received: 
{
    "resource": "/get-presigned-url",
    "path": "/get-presigned-url",
    "httpMethod": "POST",
    "headers": {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "CloudFront-Forwarded-Proto": "https",
        "CloudFront-Is-Desktop-Viewer": "true",
        "CloudFront-Is-Mobile-Viewer": "false",
        "CloudFront-Is-SmartTV-Viewer": "false",
        "CloudFront-Is-Tablet-Viewer": "false",
        "CloudFront-Viewer-ASN": "13335",
        "CloudFront-Viewer-Country": "US",
        "content-type": "application/json",
        "Host": "o7d0i4to5a.execute-api.us-west-2.amazonaws.com",
        "origin": "https://dev.hansentour.com",
        "priority": "u=3, i",
        "Referer": "https://dev.hansentour.com/",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15",
        "Via": "2.0 94d9d221defc9832eeda31acd3f6f552.cloudfront.net (CloudFront)",
        "X-Amz-Cf-Id": "Qy2hY_AqdrP4Z-ZfpJPQ-8do2-tsAtD0FnsfA8MLiFJJKhTR3b7zkQ==",
        "X-Amzn-Trace-Id": "Root=1-683a7e71-778f04621cd8112b035f4dc3",
        "X-Forwarded-For": "104.28.48.213, 3.172.27.39",
        "X-Forwarded-Port": "443",
        "X-Forwarded-Proto": "https"
    },
    "multiValueHeaders": {
        "Accept": [
            "*/*"
        ],
        "Accept-Encoding": [
            "gzip, deflate, br"
        ],
        "Accept-Language": [
            "en-US,en;q=0.9"
        ],
        "CloudFront-Forwarded-Proto": [
            "https"
        ],
        "CloudFront-Is-Desktop-Viewer": [
            "true"
        ],
        "CloudFront-Is-Mobile-Viewer": [
            "false"
        ],
        "CloudFront-Is-SmartTV-Viewer": [
            "false"
        ],
        "CloudFront-Is-Tablet-Viewer": [
            "false"
        ],
        "CloudFront-Viewer-ASN": [
            "13335"
        ],
        "CloudFront-Viewer-Country": [
            "US"
        ],
        "content-type": [
            "application/json"
        ],
        "Host": [
            "o7d0i4to5a.execute-api.us-west-2.amazonaws.com"
        ],
        "origin": [
            "https://dev.hansentour.com"
        ],
        "priority": [
            "u=3, i"
        ],
        "Referer": [
            "https://dev.hansentour.com/"
        ],
        "sec-fetch-dest": [
            "empty"
        ],
        "sec-fetch-mode": [
            "cors"
        ],
        "sec-fetch-site": [
            "cross-site"
        ],
        "User-Agent": [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15"
        ],
        "Via": [
            "2.0 94d9d221defc9832eeda31acd3f6f552.cloudfront.net (CloudFront)"
        ],
        "X-Amz-Cf-Id": [
            "Qy2hY_AqdrP4Z-ZfpJPQ-8do2-tsAtD0FnsfA8MLiFJJKhTR3b7zkQ=="
        ],
        "X-Amzn-Trace-Id": [
            "Root=1-683a7e71-778f04621cd8112b035f4dc3"
        ],
        "X-Forwarded-For": [
            "104.28.48.213, 3.172.27.39"
        ],
        "X-Forwarded-Port": [
            "443"
        ],
        "X-Forwarded-Proto": [
            "https"
        ]
    },
    "queryStringParameters": null,
    "multiValueQueryStringParameters": null,
    "pathParameters": null,
    "stageVariables": null,
    "requestContext": {
        "resourceId": "4xttcm",
        "resourcePath": "/get-presigned-url",
        "httpMethod": "POST",
        "extendedRequestId": "Laix1F67PHcEhbQ=",
        "requestTime": "31/May/2025:03:58:41 +0000",
        "path": "/prod/get-presigned-url",
        "accountId": "975050048887",
        "protocol": "HTTP/1.1",
        "stage": "prod",
        "domainPrefix": "o7d0i4to5a",
        "requestTimeEpoch": 1748663921744,
        "requestId": "af5a16f7-74c1-4b1e-8fb9-08c348517be2",
        "identity": {
            "cognitoIdentityPoolId": null,
            "accountId": null,
            "cognitoIdentityId": null,
            "caller": null,
            "sourceIp": "104.28.48.213",
            "principalOrgId": null,
            "accessKey": null,
            "cognitoAuthenticationType": null,
            "cognitoAuthenticationProvider": null,
            "userArn": null,
            "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15",
            "user": null
        },
        "domainName": "o7d0i4to5a.execute-api.us-west-2.amazonaws.com",
        "deploymentId": "83bgxq",
        "apiId": "o7d0i4to5a"
    },
    "body": "{\"uploadId\":\"LPHQdRuwSSissIM1GmDiB_L_Eoun68VuNI_VF02m1g_1eWoczBd3ErEkYdg4l8ljRZhE34TyVrCwzgVHi1Dn7MDl.4SXArRWKnAMrvG9Rzj6kdQ1HCb3WiPtdAG3LG_vYFZsNg9.xEd08dRQH2.vcLNr0Ilp8QitH04icxURJLk-\",\"bucketName\":\"spaceport-uploads\",\"objectKey\":\"1748663920512-5nvr6q-Archive.zip\",\"partNumber\":1}",
    "isBase64Encoded": false
}


2025-05-31T03:58:41.759Z 6024a5ff-0783-4df3-aaf2-e2af855ec92e INFO Event received: {"resource":"/get-presigned-url","path":"/get-presigned-url","httpMethod":"POST","headers":{"Accept":"*/*","Accept-Encoding":"gzip, deflate, br","Accept-Language":"en-US,en;q=0.9","CloudFront-Forwarded-Proto":"https","CloudFront-Is-Desktop-Viewer":"true","CloudFront-Is-Mobile-Viewer":"false","CloudFront-Is-SmartTV-Viewer":"false","CloudFront-Is-Tablet-Viewer":"false","CloudFront-Viewer-ASN":"13335","CloudFront-Viewer-Country":"US","content-type":"application/json","Host":"o7d0i4to5a.execute-api.us-west-2.amazonaws.com","origin":"https://dev.hansentour.com","priority":"u=3, i","Referer":"https://dev.hansentour.com/","sec-fetch-dest":"empty","sec-fetch-mode":"cors","sec-fetch-site":"cross-site","User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15","Via":"2.0 94d9d221defc9832eeda31acd3f6f552.cloudfront.net (CloudFront)","X-Amz-Cf-Id":"Qy2hY_AqdrP4Z-ZfpJPQ-8do2-tsAtD0FnsfA8MLiFJJKhTR3b7zkQ==","X-Amzn-Trace-Id":"Root=1-683a7e71-778f04621cd8112b035f4dc3","X-Forwarded-For":"104.28.48.213, 3.172.27.39","X-Forwarded-Port":"443","X-Forwarded-Proto":"https"},"multiValueHeaders":{"Accept":["*/*"],"Accept-Encoding":["gzip, deflate, br"],"Accept-Language":["en-US,en;q=0.9"],"CloudFront-Forwarded-Proto":["https"],"CloudFront-Is-Desktop-Viewer":["true"],"CloudFront-Is-Mobile-Viewer":["false"],"CloudFront-Is-SmartTV-Viewer":["false"],"CloudFront-Is-Tablet-Viewer":["false"],"CloudFront-Viewer-ASN":["13335"],"CloudFront-Viewer-Country":["US"],"content-type":["application/json"],"Host":["o7d0i4to5a.execute-api.us-west-2.amazonaws.com"],"origin":["https://dev.hansentour.com"],"priority":["u=3, i"],"Referer":["https://dev.hansentour.com/"],"sec-fetch-dest":["empty"],"sec-fetch-mode":["cors"],"sec-fetch-site":["cross-site"],"User-Agent":["Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15"],"Via":["2.0 94d9d221defc9832eeda31acd3f6f552.cloudfront.net (CloudFront)"],"X-Amz-Cf-Id":["Qy2hY_AqdrP4Z-ZfpJPQ-8do2-tsAtD0FnsfA8MLiFJJKhTR3b7zkQ=="],"X-Amzn-Trace-Id":["Root=1-683a7e71-778f04621cd8112b035f4dc3"],"X-Forwarded-For":["104.28.48.213, 3.172.27.39"],"X-Forwarded-Port":["443"],"X-Forwarded-Proto":["https"]},"queryStringParameters":null,"multiValueQueryStringParameters":null,"pathParameters":null,"stageVariables":null,"requestContext":{"resourceId":"4xttcm","resourcePath":"/get-presigned-url","httpMethod":"POST","extendedRequestId":"Laix1F67PHcEhbQ=","requestTime":"31/May/2025:03:58:41 +0000","path":"/prod/get-presigned-url","accountId":"975050048887","protocol":"HTTP/1.1","stage":"prod","domainPrefix":"o7d0i4to5a","requestTimeEpoch":1748663921744,"requestId":"af5a16f7-74c1-4b1e-8fb9-08c348517be2","identity":{"cognitoIdentityPoolId":null,"accountId":null,"cognitoIdentityId":null,"caller":null,"sourceIp":"104.28.48.213","principalOrgId":null,"accessKey":null,"cognitoAuthenticationType":null,"cognitoAuthenticationProvider":null,"userArn":null,"userAgent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15","user":null},"domainName":"o7d0i4to5a.execute-api.us-west-2.amazonaws.com","deploymentId":"83bgxq","apiId":"o7d0i4to5a"},"body":"{\"uploadId\":\"LPHQdRuwSSissIM1GmDiB_L_Eoun68VuNI_VF02m1g_1eWoczBd3ErEkYdg4l8ljRZhE34TyVrCwzgVHi1Dn7MDl.4SXArRWKnAMrvG9Rzj6kdQ1HCb3WiPtdAG3LG_vYFZsNg9.xEd08dRQH2.vcLNr0Ilp8QitH04icxURJLk-\",\"bucketName\":\"spaceport-uploads\",\"objectKey\":\"1748663920512-5nvr6q-Archive.zip\",\"partNumber\":1}","isBase64Encoded":false}
2025-05-30T21:58:41.759-06:00
2025-05-31T03:58:41.759Z	6024a5ff-0783-4df3-aaf2-e2af855ec92e	INFO	Path: /get-presigned-url

2025-05-31T03:58:41.759Z 6024a5ff-0783-4df3-aaf2-e2af855ec92e INFO Path: /get-presigned-url
2025-05-30T21:58:41.834-06:00
2025-05-31T03:58:41.834Z	6024a5ff-0783-4df3-aaf2-e2af855ec92e	INFO	Presigned URL for part: 1 https://spaceport-uploads.s3.us-west-2.amazonaws.com/1748663920512-5nvr6q-Archive.zip?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIA6GBMDAV3VK5JL5OU%2F20250531%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20250531T035841Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEOz%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJGMEQCIH6A2%2BhHeaALyB%2ByNL%2B2qauUWr0nZuDSDTV3aEHPp8emAiBRw587r5DFS3evbd45vvR9Uf1m%2B7cCRp0B6i7j7KGOryqWAwi1%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAAaDDk3NTA1MDA0ODg4NyIMpIobJ5kRCVe5vFG9KuoCgxIGqR8t9ku202yRjv1baFBhmZ56qG0EqsmyqsGCR32ktK5sw5BM4tKwlMfR%2F0CC3n%2FnMZ6e0yecmmKZJ3a%2Bo4V2oryUFvAyZUANBfBxamHjji3cl2LwOVq%2Bjx%2FWH3Cn68W5kE0qVUgJ4tobHgR73pPqORfB7urDqsozKsJx6l9BtbwH5G60sF8W6ZYKZLA%2F%2B7rGQljExBjC4tPYCchp%2BCTamhMoeb9AK0NiQJPnpyJOK3rw8NVUxggR1kNy8XXP1ZedYd%2Bazsdl2XNK4crbj5DT1IFHyYxBO7LqWdanfFYRYoe2EE2sBRR3mmOCcPDD0B4zsbdTTZcMJWGVLUbn6LfMuvd%2Bi0L02yCCJy2GG4nLJMd55AngN7Q0U1zff%2B%2FMg%2FQ4onMsFHrRrwH93dhbzkTUqLP0Qz1p5SNvBPNRACceCLCfWWAZH4OGADgybqHFswtcmaeRu6oz9Q2BCz6On8JiYLMYC6eJDSUw7%2FzpwQY6ngHQ4qlk7uyaADOdk0Oj0KVRiEz2V3Pe35XbJkx8NW2yqcR%2BCq4IsF%2B4XjGErz0cf3S%2Fwdv5EBbudqCB5mGm4MrgN2ZFVoV1fDSR8XnRe87%2Bs9FoLTWYxAuNPUyIvP19GfQcXapL1AM08Y2hmvcZrGmJfgtkd0BBwkwmOzfGlwyjyitvKry8GJwSTsAzwEjP0vjfxIcMO0vElfTVvP2Iwg%3D%3D&X-Amz-Signature=91e24d0af48da9f0eec09abd44656d87fc0e237fbdbeb7ba1e7995ff14286d27&X-Amz-SignedHeaders=host&partNumber=1&uploadId=LPHQdRuwSSissIM1GmDiB_L_Eoun68VuNI_VF02m1g_1eWoczBd3ErEkYdg4l8ljRZhE34TyVrCwzgVHi1Dn7MDl.4SXArRWKnAMrvG9Rzj6kdQ1HCb3WiPtdAG3LG_vYFZsNg9.xEd08dRQH2.vcLNr0Ilp8QitH04icxURJLk-&x-amz-checksum-crc32=AAAAAA%3D%3D&x-amz-sdk-checksum-algorithm=CRC32&x-id=UploadPart

2025-05-31T03:58:41.834Z 6024a5ff-0783-4df3-aaf2-e2af855ec92e INFO Presigned URL for part: 1 https://spaceport-uploads.s3.us-west-2.amazonaws.com/1748663920512-5nvr6q-Archive.zip?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIA6GBMDAV3VK5JL5OU%2F20250531%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20250531T035841Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEOz%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJGMEQCIH6A2%2BhHeaALyB%2ByNL%2B2qauUWr0nZuDSDTV3aEHPp8emAiBRw587r5DFS3evbd45vvR9Uf1m%2B7cCRp0B6i7j7KGOryqWAwi1%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAAaDDk3NTA1MDA0ODg4NyIMpIobJ5kRCVe5vFG9KuoCgxIGqR8t9ku202yRjv1baFBhmZ56qG0EqsmyqsGCR32ktK5sw5BM4tKwlMfR%2F0CC3n%2FnMZ6e0yecmmKZJ3a%2Bo4V2oryUFvAyZUANBfBxamHjji3cl2LwOVq%2Bjx%2FWH3Cn68W5kE0qVUgJ4tobHgR73pPqORfB7urDqsozKsJx6l9BtbwH5G60sF8W6ZYKZLA%2F%2B7rGQljExBjC4tPYCchp%2BCTamhMoeb9AK0NiQJPnpyJOK3rw8NVUxggR1kNy8XXP1ZedYd%2Bazsdl2XNK4crbj5DT1IFHyYxBO7LqWdanfFYRYoe2EE2sBRR3mmOCcPDD0B4zsbdTTZcMJWGVLUbn6LfMuvd%2Bi0L02yCCJy2GG4nLJMd55AngN7Q0U1zff%2B%2FMg%2FQ4onMsFHrRrwH93dhbzkTUqLP0Qz1p5SNvBPNRACceCLCfWWAZH4OGADgybqHFswtcmaeRu6oz9Q2BCz6On8JiYLMYC6eJDSUw7%2FzpwQY6ngHQ4qlk7uyaADOdk0Oj0KVRiEz2V3Pe35XbJkx8NW2yqcR%2BCq4IsF%2B4XjGErz0cf3S%2Fwdv5EBbudqCB5mGm4MrgN2ZFVoV1fDSR8XnRe87%2Bs9FoLTWYxAuNPUyIvP19GfQcXapL1AM08Y2hmvcZrGmJfgtkd0BBwkwmOzfGlwyjyitvKry8GJwSTsAzwEjP0vjfxIcMO0vElfTVvP2Iwg%3D%3D&X-Amz-Signature=91e24d0af48da9f0eec09abd44656d87fc0e237fbdbeb7ba1e7995ff14286d27&X-Amz-SignedHeaders=host&partNumber=1&uploadId=LPHQdRuwSSissIM1GmDiB_L_Eoun68VuNI_VF02m1g_1eWoczBd3ErEkYdg4l8ljRZhE34TyVrCwzgVHi1Dn7MDl.4SXArRWKnAMrvG9Rzj6kdQ1HCb3WiPtdAG3LG_vYFZsNg9.xEd08dRQH2.vcLNr0Ilp8QitH04icxURJLk-&x-amz-checksum-crc32=AAAAAA%3D%3D&x-amz-sdk-checksum-algorithm=CRC32&x-id=UploadPart
2025-05-30T21:58:41.873-06:00
END RequestId: 6024a5ff-0783-4df3-aaf2-e2af855ec92e

END RequestId: 6024a5ff-0783-4df3-aaf2-e2af855ec92e
2025-05-30T21:58:41.873-06:00
REPORT RequestId: 6024a5ff-0783-4df3-aaf2-e2af855ec92e	Duration: 114.50 ms	Billed Duration: 115 ms	Memory Size: 128 MB	Max Memory Used: 91 MB	

REPORT RequestId: 6024a5ff-0783-4df3-aaf2-e2af855ec92e Duration: 114.50 ms Billed Duration: 115 ms Memory Size: 128 MB Max Memory Used: 91 MB
2025-05-30T21:59:03.832-06:00
2025-05-31T03:59:03.832Z	b1331480-1831-45d7-a365-1afb70a2da06	INFO	Event received: 
{
    "resource": "/get-presigned-url",
    "path": "/get-presigned-url",
    "httpMethod": "POST",
    "headers": {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "CloudFront-Forwarded-Proto": "https",
        "CloudFront-Is-Desktop-Viewer": "true",
        "CloudFront-Is-Mobile-Viewer": "false",
        "CloudFront-Is-SmartTV-Viewer": "false",
        "CloudFront-Is-Tablet-Viewer": "false",
        "CloudFront-Viewer-ASN": "13335",
        "CloudFront-Viewer-Country": "US",
        "content-type": "application/json",
        "Host": "o7d0i4to5a.execute-api.us-west-2.amazonaws.com",
        "origin": "https://dev.hansentour.com",
        "priority": "u=3, i",
        "Referer": "https://dev.hansentour.com/",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15",
        "Via": "2.0 94d9d221defc9832eeda31acd3f6f552.cloudfront.net (CloudFront)",
        "X-Amz-Cf-Id": "rbWsJ6noXq8tDDMuVIBbaBfg9scH80CCOc8EFvZrAW_ETdp_Knix1w==",
        "X-Amzn-Trace-Id": "Root=1-683a7e87-57b3c42d137f4b936e7b6c4c",
        "X-Forwarded-For": "104.28.48.213, 3.172.27.38",
        "X-Forwarded-Port": "443",
        "X-Forwarded-Proto": "https"
    },
    "multiValueHeaders": {
        "Accept": [
            "*/*"
        ],
        "Accept-Encoding": [
            "gzip, deflate, br"
        ],
        "Accept-Language": [
            "en-US,en;q=0.9"
        ],
        "CloudFront-Forwarded-Proto": [
            "https"
        ],
        "CloudFront-Is-Desktop-Viewer": [
            "true"
        ],
        "CloudFront-Is-Mobile-Viewer": [
            "false"
        ],
        "CloudFront-Is-SmartTV-Viewer": [
            "false"
        ],
        "CloudFront-Is-Tablet-Viewer": [
            "false"
        ],
        "CloudFront-Viewer-ASN": [
            "13335"
        ],
        "CloudFront-Viewer-Country": [
            "US"
        ],
        "content-type": [
            "application/json"
        ],
        "Host": [
            "o7d0i4to5a.execute-api.us-west-2.amazonaws.com"
        ],
        "origin": [
            "https://dev.hansentour.com"
        ],
        "priority": [
            "u=3, i"
        ],
        "Referer": [
            "https://dev.hansentour.com/"
        ],
        "sec-fetch-dest": [
            "empty"
        ],
        "sec-fetch-mode": [
            "cors"
        ],
        "sec-fetch-site": [
            "cross-site"
        ],
        "User-Agent": [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15"
        ],
        "Via": [
            "2.0 94d9d221defc9832eeda31acd3f6f552.cloudfront.net (CloudFront)"
        ],
        "X-Amz-Cf-Id": [
            "rbWsJ6noXq8tDDMuVIBbaBfg9scH80CCOc8EFvZrAW_ETdp_Knix1w=="
        ],
        "X-Amzn-Trace-Id": [
            "Root=1-683a7e87-57b3c42d137f4b936e7b6c4c"
        ],
        "X-Forwarded-For": [
            "104.28.48.213, 3.172.27.38"
        ],
        "X-Forwarded-Port": [
            "443"
        ],
        "X-Forwarded-Proto": [
            "https"
        ]
    },
    "queryStringParameters": null,
    "multiValueQueryStringParameters": null,
    "pathParameters": null,
    "stageVariables": null,
    "requestContext": {
        "resourceId": "4xttcm",
        "resourcePath": "/get-presigned-url",
        "httpMethod": "POST",
        "extendedRequestId": "Lai1RG5jvHcEfug=",
        "requestTime": "31/May/2025:03:59:03 +0000",
        "path": "/prod/get-presigned-url",
        "accountId": "975050048887",
        "protocol": "HTTP/1.1",
        "stage": "prod",
        "domainPrefix": "o7d0i4to5a",
        "requestTimeEpoch": 1748663943788,
        "requestId": "67fd45fb-1f05-4758-b0ec-7d201e1624c9",
        "identity": {
            "cognitoIdentityPoolId": null,
            "accountId": null,
            "cognitoIdentityId": null,
            "caller": null,
            "sourceIp": "104.28.48.213",
            "principalOrgId": null,
            "accessKey": null,
            "cognitoAuthenticationType": null,
            "cognitoAuthenticationProvider": null,
            "userArn": null,
            "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15",
            "user": null
        },
        "domainName": "o7d0i4to5a.execute-api.us-west-2.amazonaws.com",
        "deploymentId": "83bgxq",
        "apiId": "o7d0i4to5a"
    },
    "body": "{\"uploadId\":\"LPHQdRuwSSissIM1GmDiB_L_Eoun68VuNI_VF02m1g_1eWoczBd3ErEkYdg4l8ljRZhE34TyVrCwzgVHi1Dn7MDl.4SXArRWKnAMrvG9Rzj6kdQ1HCb3WiPtdAG3LG_vYFZsNg9.xEd08dRQH2.vcLNr0Ilp8QitH04icxURJLk-\",\"bucketName\":\"spaceport-uploads\",\"objectKey\":\"1748663920512-5nvr6q-Archive.zip\",\"partNumber\":2}",
    "isBase64Encoded": false
}


2025-05-31T03:59:03.832Z b1331480-1831-45d7-a365-1afb70a2da06 INFO Event received: {"resource":"/get-presigned-url","path":"/get-presigned-url","httpMethod":"POST","headers":{"Accept":"*/*","Accept-Encoding":"gzip, deflate, br","Accept-Language":"en-US,en;q=0.9","CloudFront-Forwarded-Proto":"https","CloudFront-Is-Desktop-Viewer":"true","CloudFront-Is-Mobile-Viewer":"false","CloudFront-Is-SmartTV-Viewer":"false","CloudFront-Is-Tablet-Viewer":"false","CloudFront-Viewer-ASN":"13335","CloudFront-Viewer-Country":"US","content-type":"application/json","Host":"o7d0i4to5a.execute-api.us-west-2.amazonaws.com","origin":"https://dev.hansentour.com","priority":"u=3, i","Referer":"https://dev.hansentour.com/","sec-fetch-dest":"empty","sec-fetch-mode":"cors","sec-fetch-site":"cross-site","User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15","Via":"2.0 94d9d221defc9832eeda31acd3f6f552.cloudfront.net (CloudFront)","X-Amz-Cf-Id":"rbWsJ6noXq8tDDMuVIBbaBfg9scH80CCOc8EFvZrAW_ETdp_Knix1w==","X-Amzn-Trace-Id":"Root=1-683a7e87-57b3c42d137f4b936e7b6c4c","X-Forwarded-For":"104.28.48.213, 3.172.27.38","X-Forwarded-Port":"443","X-Forwarded-Proto":"https"},"multiValueHeaders":{"Accept":["*/*"],"Accept-Encoding":["gzip, deflate, br"],"Accept-Language":["en-US,en;q=0.9"],"CloudFront-Forwarded-Proto":["https"],"CloudFront-Is-Desktop-Viewer":["true"],"CloudFront-Is-Mobile-Viewer":["false"],"CloudFront-Is-SmartTV-Viewer":["false"],"CloudFront-Is-Tablet-Viewer":["false"],"CloudFront-Viewer-ASN":["13335"],"CloudFront-Viewer-Country":["US"],"content-type":["application/json"],"Host":["o7d0i4to5a.execute-api.us-west-2.amazonaws.com"],"origin":["https://dev.hansentour.com"],"priority":["u=3, i"],"Referer":["https://dev.hansentour.com/"],"sec-fetch-dest":["empty"],"sec-fetch-mode":["cors"],"sec-fetch-site":["cross-site"],"User-Agent":["Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15"],"Via":["2.0 94d9d221defc9832eeda31acd3f6f552.cloudfront.net (CloudFront)"],"X-Amz-Cf-Id":["rbWsJ6noXq8tDDMuVIBbaBfg9scH80CCOc8EFvZrAW_ETdp_Knix1w=="],"X-Amzn-Trace-Id":["Root=1-683a7e87-57b3c42d137f4b936e7b6c4c"],"X-Forwarded-For":["104.28.48.213, 3.172.27.38"],"X-Forwarded-Port":["443"],"X-Forwarded-Proto":["https"]},"queryStringParameters":null,"multiValueQueryStringParameters":null,"pathParameters":null,"stageVariables":null,"requestContext":{"resourceId":"4xttcm","resourcePath":"/get-presigned-url","httpMethod":"POST","extendedRequestId":"Lai1RG5jvHcEfug=","requestTime":"31/May/2025:03:59:03 +0000","path":"/prod/get-presigned-url","accountId":"975050048887","protocol":"HTTP/1.1","stage":"prod","domainPrefix":"o7d0i4to5a","requestTimeEpoch":1748663943788,"requestId":"67fd45fb-1f05-4758-b0ec-7d201e1624c9","identity":{"cognitoIdentityPoolId":null,"accountId":null,"cognitoIdentityId":null,"caller":null,"sourceIp":"104.28.48.213","principalOrgId":null,"accessKey":null,"cognitoAuthenticationType":null,"cognitoAuthenticationProvider":null,"userArn":null,"userAgent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15","user":null},"domainName":"o7d0i4to5a.execute-api.us-west-2.amazonaws.com","deploymentId":"83bgxq","apiId":"o7d0i4to5a"},"body":"{\"uploadId\":\"LPHQdRuwSSissIM1GmDiB_L_Eoun68VuNI_VF02m1g_1eWoczBd3ErEkYdg4l8ljRZhE34TyVrCwzgVHi1Dn7MDl.4SXArRWKnAMrvG9Rzj6kdQ1HCb3WiPtdAG3LG_vYFZsNg9.xEd08dRQH2.vcLNr0Ilp8QitH04icxURJLk-\",\"bucketName\":\"spaceport-uploads\",\"objectKey\":\"1748663920512-5nvr6q-Archive.zip\",\"partNumber\":2}","isBase64Encoded":false}
2025-05-30T21:59:03.832-06:00
START RequestId: b1331480-1831-45d7-a365-1afb70a2da06 Version: $LATEST

START RequestId: b1331480-1831-45d7-a365-1afb70a2da06 Version: $LATEST
2025-05-30T21:59:03.833-06:00
2025-05-31T03:59:03.833Z	b1331480-1831-45d7-a365-1afb70a2da06	INFO	Path: /get-presigned-url

2025-05-31T03:59:03.833Z b1331480-1831-45d7-a365-1afb70a2da06 INFO Path: /get-presigned-url
2025-05-30T21:59:03.835-06:00
2025-05-31T03:59:03.835Z	b1331480-1831-45d7-a365-1afb70a2da06	INFO	Presigned URL for part: 2 https://spaceport-uploads.s3.us-west-2.amazonaws.com/1748663920512-5nvr6q-Archive.zip?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIA6GBMDAV3VK5JL5OU%2F20250531%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20250531T035903Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEOz%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJGMEQCIH6A2%2BhHeaALyB%2ByNL%2B2qauUWr0nZuDSDTV3aEHPp8emAiBRw587r5DFS3evbd45vvR9Uf1m%2B7cCRp0B6i7j7KGOryqWAwi1%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAAaDDk3NTA1MDA0ODg4NyIMpIobJ5kRCVe5vFG9KuoCgxIGqR8t9ku202yRjv1baFBhmZ56qG0EqsmyqsGCR32ktK5sw5BM4tKwlMfR%2F0CC3n%2FnMZ6e0yecmmKZJ3a%2Bo4V2oryUFvAyZUANBfBxamHjji3cl2LwOVq%2Bjx%2FWH3Cn68W5kE0qVUgJ4tobHgR73pPqORfB7urDqsozKsJx6l9BtbwH5G60sF8W6ZYKZLA%2F%2B7rGQljExBjC4tPYCchp%2BCTamhMoeb9AK0NiQJPnpyJOK3rw8NVUxggR1kNy8XXP1ZedYd%2Bazsdl2XNK4crbj5DT1IFHyYxBO7LqWdanfFYRYoe2EE2sBRR3mmOCcPDD0B4zsbdTTZcMJWGVLUbn6LfMuvd%2Bi0L02yCCJy2GG4nLJMd55AngN7Q0U1zff%2B%2FMg%2FQ4onMsFHrRrwH93dhbzkTUqLP0Qz1p5SNvBPNRACceCLCfWWAZH4OGADgybqHFswtcmaeRu6oz9Q2BCz6On8JiYLMYC6eJDSUw7%2FzpwQY6ngHQ4qlk7uyaADOdk0Oj0KVRiEz2V3Pe35XbJkx8NW2yqcR%2BCq4IsF%2B4XjGErz0cf3S%2Fwdv5EBbudqCB5mGm4MrgN2ZFVoV1fDSR8XnRe87%2Bs9FoLTWYxAuNPUyIvP19GfQcXapL1AM08Y2hmvcZrGmJfgtkd0BBwkwmOzfGlwyjyitvKry8GJwSTsAzwEjP0vjfxIcMO0vElfTVvP2Iwg%3D%3D&X-Amz-Signature=83f6e2b14c372f8a08fdc742d7244476289a1e6db66cd14f2c620822708e2ce5&X-Amz-SignedHeaders=host&partNumber=2&uploadId=LPHQdRuwSSissIM1GmDiB_L_Eoun68VuNI_VF02m1g_1eWoczBd3ErEkYdg4l8ljRZhE34TyVrCwzgVHi1Dn7MDl.4SXArRWKnAMrvG9Rzj6kdQ1HCb3WiPtdAG3LG_vYFZsNg9.xEd08dRQH2.vcLNr0Ilp8QitH04icxURJLk-&x-amz-checksum-crc32=AAAAAA%3D%3D&x-amz-sdk-checksum-algorithm=CRC32&x-id=UploadPart

2025-05-31T03:59:03.835Z b1331480-1831-45d7-a365-1afb70a2da06 INFO Presigned URL for part: 2 https://spaceport-uploads.s3.us-west-2.amazonaws.com/1748663920512-5nvr6q-Archive.zip?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIA6GBMDAV3VK5JL5OU%2F20250531%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20250531T035903Z&X-Amz-Expires=3600&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEOz%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJGMEQCIH6A2%2BhHeaALyB%2ByNL%2B2qauUWr0nZuDSDTV3aEHPp8emAiBRw587r5DFS3evbd45vvR9Uf1m%2B7cCRp0B6i7j7KGOryqWAwi1%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAAaDDk3NTA1MDA0ODg4NyIMpIobJ5kRCVe5vFG9KuoCgxIGqR8t9ku202yRjv1baFBhmZ56qG0EqsmyqsGCR32ktK5sw5BM4tKwlMfR%2F0CC3n%2FnMZ6e0yecmmKZJ3a%2Bo4V2oryUFvAyZUANBfBxamHjji3cl2LwOVq%2Bjx%2FWH3Cn68W5kE0qVUgJ4tobHgR73pPqORfB7urDqsozKsJx6l9BtbwH5G60sF8W6ZYKZLA%2F%2B7rGQljExBjC4tPYCchp%2BCTamhMoeb9AK0NiQJPnpyJOK3rw8NVUxggR1kNy8XXP1ZedYd%2Bazsdl2XNK4crbj5DT1IFHyYxBO7LqWdanfFYRYoe2EE2sBRR3mmOCcPDD0B4zsbdTTZcMJWGVLUbn6LfMuvd%2Bi0L02yCCJy2GG4nLJMd55AngN7Q0U1zff%2B%2FMg%2FQ4onMsFHrRrwH93dhbzkTUqLP0Qz1p5SNvBPNRACceCLCfWWAZH4OGADgybqHFswtcmaeRu6oz9Q2BCz6On8JiYLMYC6eJDSUw7%2FzpwQY6ngHQ4qlk7uyaADOdk0Oj0KVRiEz2V3Pe35XbJkx8NW2yqcR%2BCq4IsF%2B4XjGErz0cf3S%2Fwdv5EBbudqCB5mGm4MrgN2ZFVoV1fDSR8XnRe87%2Bs9FoLTWYxAuNPUyIvP19GfQcXapL1AM08Y2hmvcZrGmJfgtkd0BBwkwmOzfGlwyjyitvKry8GJwSTsAzwEjP0vjfxIcMO0vElfTVvP2Iwg%3D%3D&X-Amz-Signature=83f6e2b14c372f8a08fdc742d7244476289a1e6db66cd14f2c620822708e2ce5&X-Amz-SignedHeaders=host&partNumber=2&uploadId=LPHQdRuwSSissIM1GmDiB_L_Eoun68VuNI_VF02m1g_1eWoczBd3ErEkYdg4l8ljRZhE34TyVrCwzgVHi1Dn7MDl.4SXArRWKnAMrvG9Rzj6kdQ1HCb3WiPtdAG3LG_vYFZsNg9.xEd08dRQH2.vcLNr0Ilp8QitH04icxURJLk-&x-amz-checksum-crc32=AAAAAA%3D%3D&x-amz-sdk-checksum-algorithm=CRC32&x-id=UploadPart
2025-05-30T21:59:03.873-06:00
END RequestId: b1331480-1831-45d7-a365-1afb70a2da06

END RequestId: b1331480-1831-45d7-a365-1afb70a2da06
2025-05-30T21:59:03.873-06:00
REPORT RequestId: b1331480-1831-45d7-a365-1afb70a2da06	Duration: 52.15 ms	Billed Duration: 53 ms	Memory Size: 128 MB	Max Memory Used: 91 MB	

REPORT RequestId: b1331480-1831-45d7-a365-1afb70a2da06 Duration: 52.15 ms Billed Duration: 53 ms Memory Size: 128 MB Max Memory Used: 91 MB
2025-05-30T21:59:13.227-06:00
2025-05-31T03:59:13.227Z	f7227f91-cc16-40d1-b25c-f9a91cfcd3ce	INFO	Event received: 
{
    "resource": "/complete-multipart-upload",
    "path": "/complete-multipart-upload",
    "httpMethod": "POST",
    "headers": {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "CloudFront-Forwarded-Proto": "https",
        "CloudFront-Is-Desktop-Viewer": "true",
        "CloudFront-Is-Mobile-Viewer": "false",
        "CloudFront-Is-SmartTV-Viewer": "false",
        "CloudFront-Is-Tablet-Viewer": "false",
        "CloudFront-Viewer-ASN": "13335",
        "CloudFront-Viewer-Country": "US",
        "content-type": "application/json",
        "Host": "o7d0i4to5a.execute-api.us-west-2.amazonaws.com",
        "origin": "https://dev.hansentour.com",
        "priority": "u=3, i",
        "Referer": "https://dev.hansentour.com/",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15",
        "Via": "2.0 94d9d221defc9832eeda31acd3f6f552.cloudfront.net (CloudFront)",
        "X-Amz-Cf-Id": "RPUZcnEfBnx1kZv7iYYPHa5Fz4c9j53C_2ta5mWVCL-MXKGzI9Qw3A==",
        "X-Amzn-Trace-Id": "Root=1-683a7e91-1a0193f06ef6674c63866a9e",
        "X-Forwarded-For": "104.28.48.213, 3.172.27.46",
        "X-Forwarded-Port": "443",
        "X-Forwarded-Proto": "https"
    },
    "multiValueHeaders": {
        "Accept": [
            "*/*"
        ],
        "Accept-Encoding": [
            "gzip, deflate, br"
        ],
        "Accept-Language": [
            "en-US,en;q=0.9"
        ],
        "CloudFront-Forwarded-Proto": [
            "https"
        ],
        "CloudFront-Is-Desktop-Viewer": [
            "true"
        ],
        "CloudFront-Is-Mobile-Viewer": [
            "false"
        ],
        "CloudFront-Is-SmartTV-Viewer": [
            "false"
        ],
        "CloudFront-Is-Tablet-Viewer": [
            "false"
        ],
        "CloudFront-Viewer-ASN": [
            "13335"
        ],
        "CloudFront-Viewer-Country": [
            "US"
        ],
        "content-type": [
            "application/json"
        ],
        "Host": [
            "o7d0i4to5a.execute-api.us-west-2.amazonaws.com"
        ],
        "origin": [
            "https://dev.hansentour.com"
        ],
        "priority": [
            "u=3, i"
        ],
        "Referer": [
            "https://dev.hansentour.com/"
        ],
        "sec-fetch-dest": [
            "empty"
        ],
        "sec-fetch-mode": [
            "cors"
        ],
        "sec-fetch-site": [
            "cross-site"
        ],
        "User-Agent": [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15"
        ],
        "Via": [
            "2.0 94d9d221defc9832eeda31acd3f6f552.cloudfront.net (CloudFront)"
        ],
        "X-Amz-Cf-Id": [
            "RPUZcnEfBnx1kZv7iYYPHa5Fz4c9j53C_2ta5mWVCL-MXKGzI9Qw3A=="
        ],
        "X-Amzn-Trace-Id": [
            "Root=1-683a7e91-1a0193f06ef6674c63866a9e"
        ],
        "X-Forwarded-For": [
            "104.28.48.213, 3.172.27.46"
        ],
        "X-Forwarded-Port": [
            "443"
        ],
        "X-Forwarded-Proto": [
            "https"
        ]
    },
    "queryStringParameters": null,
    "multiValueQueryStringParameters": null,
    "pathParameters": null,
    "stageVariables": null,
    "requestContext": {
        "resourceId": "s6sz5x",
        "resourcePath": "/complete-multipart-upload",
        "httpMethod": "POST",
        "extendedRequestId": "Lai2vH1DvHcEeqw=",
        "requestTime": "31/May/2025:03:59:13 +0000",
        "path": "/prod/complete-multipart-upload",
        "accountId": "975050048887",
        "protocol": "HTTP/1.1",
        "stage": "prod",
        "domainPrefix": "o7d0i4to5a",
        "requestTimeEpoch": 1748663953189,
        "requestId": "09c07e38-b70f-4749-9c8a-ed52c4bbe266",
        "identity": {
            "cognitoIdentityPoolId": null,
            "accountId": null,
            "cognitoIdentityId": null,
            "caller": null,
            "sourceIp": "104.28.48.213",
            "principalOrgId": null,
            "accessKey": null,
            "cognitoAuthenticationType": null,
            "cognitoAuthenticationProvider": null,
            "userArn": null,
            "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15",
            "user": null
        },
        "domainName": "o7d0i4to5a.execute-api.us-west-2.amazonaws.com",
        "deploymentId": "83bgxq",
        "apiId": "o7d0i4to5a"
    },
    "body": "{\"uploadId\":\"LPHQdRuwSSissIM1GmDiB_L_Eoun68VuNI_VF02m1g_1eWoczBd3ErEkYdg4l8ljRZhE34TyVrCwzgVHi1Dn7MDl.4SXArRWKnAMrvG9Rzj6kdQ1HCb3WiPtdAG3LG_vYFZsNg9.xEd08dRQH2.vcLNr0Ilp8QitH04icxURJLk-\",\"bucketName\":\"spaceport-uploads\",\"objectKey\":\"1748663920512-5nvr6q-Archive.zip\",\"parts\":[{\"ETag\":\"\\\"89fad9e3c85cdc9e7d93c268aa99b15f\\\"\",\"PartNumber\":1},{\"ETag\":\"\\\"b0ab84dd9e9e98122d6b4d2fa483da06\\\"\",\"PartNumber\":2}]}",
    "isBase64Encoded": false
}


2025-05-31T03:59:13.227Z f7227f91-cc16-40d1-b25c-f9a91cfcd3ce INFO Event received: {"resource":"/complete-multipart-upload","path":"/complete-multipart-upload","httpMethod":"POST","headers":{"Accept":"*/*","Accept-Encoding":"gzip, deflate, br","Accept-Language":"en-US,en;q=0.9","CloudFront-Forwarded-Proto":"https","CloudFront-Is-Desktop-Viewer":"true","CloudFront-Is-Mobile-Viewer":"false","CloudFront-Is-SmartTV-Viewer":"false","CloudFront-Is-Tablet-Viewer":"false","CloudFront-Viewer-ASN":"13335","CloudFront-Viewer-Country":"US","content-type":"application/json","Host":"o7d0i4to5a.execute-api.us-west-2.amazonaws.com","origin":"https://dev.hansentour.com","priority":"u=3, i","Referer":"https://dev.hansentour.com/","sec-fetch-dest":"empty","sec-fetch-mode":"cors","sec-fetch-site":"cross-site","User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15","Via":"2.0 94d9d221defc9832eeda31acd3f6f552.cloudfront.net (CloudFront)","X-Amz-Cf-Id":"RPUZcnEfBnx1kZv7iYYPHa5Fz4c9j53C_2ta5mWVCL-MXKGzI9Qw3A==","X-Amzn-Trace-Id":"Root=1-683a7e91-1a0193f06ef6674c63866a9e","X-Forwarded-For":"104.28.48.213, 3.172.27.46","X-Forwarded-Port":"443","X-Forwarded-Proto":"https"},"multiValueHeaders":{"Accept":["*/*"],"Accept-Encoding":["gzip, deflate, br"],"Accept-Language":["en-US,en;q=0.9"],"CloudFront-Forwarded-Proto":["https"],"CloudFront-Is-Desktop-Viewer":["true"],"CloudFront-Is-Mobile-Viewer":["false"],"CloudFront-Is-SmartTV-Viewer":["false"],"CloudFront-Is-Tablet-Viewer":["false"],"CloudFront-Viewer-ASN":["13335"],"CloudFront-Viewer-Country":["US"],"content-type":["application/json"],"Host":["o7d0i4to5a.execute-api.us-west-2.amazonaws.com"],"origin":["https://dev.hansentour.com"],"priority":["u=3, i"],"Referer":["https://dev.hansentour.com/"],"sec-fetch-dest":["empty"],"sec-fetch-mode":["cors"],"sec-fetch-site":["cross-site"],"User-Agent":["Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15"],"Via":["2.0 94d9d221defc9832eeda31acd3f6f552.cloudfront.net (CloudFront)"],"X-Amz-Cf-Id":["RPUZcnEfBnx1kZv7iYYPHa5Fz4c9j53C_2ta5mWVCL-MXKGzI9Qw3A=="],"X-Amzn-Trace-Id":["Root=1-683a7e91-1a0193f06ef6674c63866a9e"],"X-Forwarded-For":["104.28.48.213, 3.172.27.46"],"X-Forwarded-Port":["443"],"X-Forwarded-Proto":["https"]},"queryStringParameters":null,"multiValueQueryStringParameters":null,"pathParameters":null,"stageVariables":null,"requestContext":{"resourceId":"s6sz5x","resourcePath":"/complete-multipart-upload","httpMethod":"POST","extendedRequestId":"Lai2vH1DvHcEeqw=","requestTime":"31/May/2025:03:59:13 +0000","path":"/prod/complete-multipart-upload","accountId":"975050048887","protocol":"HTTP/1.1","stage":"prod","domainPrefix":"o7d0i4to5a","requestTimeEpoch":1748663953189,"requestId":"09c07e38-b70f-4749-9c8a-ed52c4bbe266","identity":{"cognitoIdentityPoolId":null,"accountId":null,"cognitoIdentityId":null,"caller":null,"sourceIp":"104.28.48.213","principalOrgId":null,"accessKey":null,"cognitoAuthenticationType":null,"cognitoAuthenticationProvider":null,"userArn":null,"userAgent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15","user":null},"domainName":"o7d0i4to5a.execute-api.us-west-2.amazonaws.com","deploymentId":"83bgxq","apiId":"o7d0i4to5a"},"body":"{\"uploadId\":\"LPHQdRuwSSissIM1GmDiB_L_Eoun68VuNI_VF02m1g_1eWoczBd3ErEkYdg4l8ljRZhE34TyVrCwzgVHi1Dn7MDl.4SXArRWKnAMrvG9Rzj6kdQ1HCb3WiPtdAG3LG_vYFZsNg9.xEd08dRQH2.vcLNr0Ilp8QitH04icxURJLk-\",\"bucketName\":\"spaceport-uploads\",\"objectKey\":\"1748663920512-5nvr6q-Archive.zip\",\"parts\":[{\"ETag\":\"\\\"89fad9e3c85cdc9e7d93c268aa99b15f\\\"\",\"PartNumber\":1},{\"ETag\":\"\\\"b0ab84dd9e9e98122d6b4d2fa483da06\\\"\",\"PartNumber\":2}]}","isBase64Encoded":false}
2025-05-30T21:59:13.227-06:00
2025-05-31T03:59:13.227Z	f7227f91-cc16-40d1-b25c-f9a91cfcd3ce	INFO	Path: /complete-multipart-upload

2025-05-31T03:59:13.227Z f7227f91-cc16-40d1-b25c-f9a91cfcd3ce INFO Path: /complete-multipart-upload
2025-05-30T21:59:13.227-06:00
START RequestId: f7227f91-cc16-40d1-b25c-f9a91cfcd3ce Version: $LATEST

START RequestId: f7227f91-cc16-40d1-b25c-f9a91cfcd3ce Version: $LATEST
2025-05-30T21:59:13.463-06:00
2025-05-31T03:59:13.463Z	f7227f91-cc16-40d1-b25c-f9a91cfcd3ce	INFO	Multipart upload completed: {
  '$metadata': {
    httpStatusCode: 200,
    requestId: 'J72N2GHGGPY0FFJ9',
    extendedRequestId: 'zSc1B+ZFlgm1Kl0aQCDkRgPP68mKVsmgb31OwdxHK0whKyVdkBcvEHpFp4wQX4VAb2QwLwA+xel0/oU9R6/jXQ==',
    cfId: undefined,
    attempts: 1,
    totalRetryDelay: 0
  },
  ServerSideEncryption: 'AES256',
  Bucket: 'spaceport-uploads',
  ChecksumCRC64NVME: 'ETKu6V6SyJU=',
  ChecksumType: 'FULL_OBJECT',
  ETag: '"c627c9eb963eea917feee280c462f9ec-2"',
  Key: '1748663920512-5nvr6q-Archive.zip',
  Location: 'https://spaceport-uploads.s3.us-west-2.amazonaws.com/1748663920512-5nvr6q-Archive.zip'
}

2025-05-31T03:59:13.463Z f7227f91-cc16-40d1-b25c-f9a91cfcd3ce INFO Multipart upload completed: { '$metadata': { httpStatusCode: 200, requestId: 'J72N2GHGGPY0FFJ9', extendedRequestId: 'zSc1B+ZFlgm1Kl0aQCDkRgPP68mKVsmgb31OwdxHK0whKyVdkBcvEHpFp4wQX4VAb2QwLwA+xel0/oU9R6/jXQ==', cfId: undefined, attempts: 1, totalRetryDelay: 0 }, ServerSideEncryption: 'AES256', Bucket: 'spaceport-uploads', ChecksumCRC64NVME: 'ETKu6V6SyJU=', ChecksumType: 'FULL_OBJECT', ETag: '"c627c9eb963eea917feee280c462f9ec-2"', Key: '1748663920512-5nvr6q-Archive.zip', Location: 'https://spaceport-uploads.s3.us-west-2.amazonaws.com/1748663920512-5nvr6q-Archive.zip' }
2025-05-30T21:59:13.474-06:00
END RequestId: f7227f91-cc16-40d1-b25c-f9a91cfcd3ce

END RequestId: f7227f91-cc16-40d1-b25c-f9a91cfcd3ce
2025-05-30T21:59:13.474-06:00
REPORT RequestId: f7227f91-cc16-40d1-b25c-f9a91cfcd3ce	Duration: 246.56 ms	Billed Duration: 247 ms	Memory Size: 128 MB	Max Memory Used: 91 MB	

REPORT RequestId: f7227f91-cc16-40d1-b25c-f9a91cfcd3ce Duration: 246.56 ms Billed Duration: 247 ms Memory Size: 128 MB Max Memory Used: 91 MB
2025-05-30T21:59:13.710-06:00
START RequestId: 5f2d3fc3-3374-4c9d-9d3b-350d6a38f467 Version: $LATEST

START RequestId: 5f2d3fc3-3374-4c9d-9d3b-350d6a38f467 Version: $LATEST
2025-05-30T21:59:13.711-06:00
2025-05-31T03:59:13.711Z	5f2d3fc3-3374-4c9d-9d3b-350d6a38f467	INFO	Event received: 
{
    "resource": "/save-submission",
    "path": "/save-submission",
    "httpMethod": "POST",
    "headers": {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "CloudFront-Forwarded-Proto": "https",
        "CloudFront-Is-Desktop-Viewer": "true",
        "CloudFront-Is-Mobile-Viewer": "false",
        "CloudFront-Is-SmartTV-Viewer": "false",
        "CloudFront-Is-Tablet-Viewer": "false",
        "CloudFront-Viewer-ASN": "13335",
        "CloudFront-Viewer-Country": "US",
        "content-type": "application/json",
        "Host": "o7d0i4to5a.execute-api.us-west-2.amazonaws.com",
        "origin": "https://dev.hansentour.com",
        "priority": "u=3, i",
        "Referer": "https://dev.hansentour.com/",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15",
        "Via": "2.0 94d9d221defc9832eeda31acd3f6f552.cloudfront.net (CloudFront)",
        "X-Amz-Cf-Id": "4qP_deCX8AYkBdK32q0i_Hr4DBMf78faiCIqPskQq6QUISB_rsOWlw==",
        "X-Amzn-Trace-Id": "Root=1-683a7e91-7e10636820ca6e5449987b27",
        "X-Forwarded-For": "104.28.48.213, 3.172.27.18",
        "X-Forwarded-Port": "443",
        "X-Forwarded-Proto": "https"
    },
    "multiValueHeaders": {
        "Accept": [
            "*/*"
        ],
        "Accept-Encoding": [
            "gzip, deflate, br"
        ],
        "Accept-Language": [
            "en-US,en;q=0.9"
        ],
        "CloudFront-Forwarded-Proto": [
            "https"
        ],
        "CloudFront-Is-Desktop-Viewer": [
            "true"
        ],
        "CloudFront-Is-Mobile-Viewer": [
            "false"
        ],
        "CloudFront-Is-SmartTV-Viewer": [
            "false"
        ],
        "CloudFront-Is-Tablet-Viewer": [
            "false"
        ],
        "CloudFront-Viewer-ASN": [
            "13335"
        ],
        "CloudFront-Viewer-Country": [
            "US"
        ],
        "content-type": [
            "application/json"
        ],
        "Host": [
            "o7d0i4to5a.execute-api.us-west-2.amazonaws.com"
        ],
        "origin": [
            "https://dev.hansentour.com"
        ],
        "priority": [
            "u=3, i"
        ],
        "Referer": [
            "https://dev.hansentour.com/"
        ],
        "sec-fetch-dest": [
            "empty"
        ],
        "sec-fetch-mode": [
            "cors"
        ],
        "sec-fetch-site": [
            "cross-site"
        ],
        "User-Agent": [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15"
        ],
        "Via": [
            "2.0 94d9d221defc9832eeda31acd3f6f552.cloudfront.net (CloudFront)"
        ],
        "X-Amz-Cf-Id": [
            "4qP_deCX8AYkBdK32q0i_Hr4DBMf78faiCIqPskQq6QUISB_rsOWlw=="
        ],
        "X-Amzn-Trace-Id": [
            "Root=1-683a7e91-7e10636820ca6e5449987b27"
        ],
        "X-Forwarded-For": [
            "104.28.48.213, 3.172.27.18"
        ],
        "X-Forwarded-Port": [
            "443"
        ],
        "X-Forwarded-Proto": [
            "https"
        ]
    },
    "queryStringParameters": null,
    "multiValueQueryStringParameters": null,
    "pathParameters": null,
    "stageVariables": null,
    "requestContext": {
        "resourceId": "1n92nh",
        "resourcePath": "/save-submission",
        "httpMethod": "POST",
        "extendedRequestId": "Lai20HkIPHcEDIw=",
        "requestTime": "31/May/2025:03:59:13 +0000",
        "path": "/prod/save-submission",
        "accountId": "975050048887",
        "protocol": "HTTP/1.1",
        "stage": "prod",
        "domainPrefix": "o7d0i4to5a",
        "requestTimeEpoch": 1748663953698,
        "requestId": "813e7443-d5f6-45ff-9060-272d5536dc13",
        "identity": {
            "cognitoIdentityPoolId": null,
            "accountId": null,
            "cognitoIdentityId": null,
            "caller": null,
            "sourceIp": "104.28.48.213",
            "principalOrgId": null,
            "accessKey": null,
            "cognitoAuthenticationType": null,
            "cognitoAuthenticationProvider": null,
            "userArn": null,
            "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15",
            "user": null
        },
        "domainName": "o7d0i4to5a.execute-api.us-west-2.amazonaws.com",
        "deploymentId": "83bgxq",
        "apiId": "o7d0i4to5a"
    },
    "body": "{\"email\":\"gbhbyu@gmail.com\",\"propertyTitle\":\"DummyTester\",\"listingDescription\":\"yooooaooa\",\"addressOfProperty\":\"ur mom\",\"optionalNotes\":\"oogabooga\",\"objectKey\":\"1748663920512-5nvr6q-Archive.zip\"}",
    "isBase64Encoded": false
}


2025-05-31T03:59:13.711Z 5f2d3fc3-3374-4c9d-9d3b-350d6a38f467 INFO Event received: {"resource":"/save-submission","path":"/save-submission","httpMethod":"POST","headers":{"Accept":"*/*","Accept-Encoding":"gzip, deflate, br","Accept-Language":"en-US,en;q=0.9","CloudFront-Forwarded-Proto":"https","CloudFront-Is-Desktop-Viewer":"true","CloudFront-Is-Mobile-Viewer":"false","CloudFront-Is-SmartTV-Viewer":"false","CloudFront-Is-Tablet-Viewer":"false","CloudFront-Viewer-ASN":"13335","CloudFront-Viewer-Country":"US","content-type":"application/json","Host":"o7d0i4to5a.execute-api.us-west-2.amazonaws.com","origin":"https://dev.hansentour.com","priority":"u=3, i","Referer":"https://dev.hansentour.com/","sec-fetch-dest":"empty","sec-fetch-mode":"cors","sec-fetch-site":"cross-site","User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15","Via":"2.0 94d9d221defc9832eeda31acd3f6f552.cloudfront.net (CloudFront)","X-Amz-Cf-Id":"4qP_deCX8AYkBdK32q0i_Hr4DBMf78faiCIqPskQq6QUISB_rsOWlw==","X-Amzn-Trace-Id":"Root=1-683a7e91-7e10636820ca6e5449987b27","X-Forwarded-For":"104.28.48.213, 3.172.27.18","X-Forwarded-Port":"443","X-Forwarded-Proto":"https"},"multiValueHeaders":{"Accept":["*/*"],"Accept-Encoding":["gzip, deflate, br"],"Accept-Language":["en-US,en;q=0.9"],"CloudFront-Forwarded-Proto":["https"],"CloudFront-Is-Desktop-Viewer":["true"],"CloudFront-Is-Mobile-Viewer":["false"],"CloudFront-Is-SmartTV-Viewer":["false"],"CloudFront-Is-Tablet-Viewer":["false"],"CloudFront-Viewer-ASN":["13335"],"CloudFront-Viewer-Country":["US"],"content-type":["application/json"],"Host":["o7d0i4to5a.execute-api.us-west-2.amazonaws.com"],"origin":["https://dev.hansentour.com"],"priority":["u=3, i"],"Referer":["https://dev.hansentour.com/"],"sec-fetch-dest":["empty"],"sec-fetch-mode":["cors"],"sec-fetch-site":["cross-site"],"User-Agent":["Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15"],"Via":["2.0 94d9d221defc9832eeda31acd3f6f552.cloudfront.net (CloudFront)"],"X-Amz-Cf-Id":["4qP_deCX8AYkBdK32q0i_Hr4DBMf78faiCIqPskQq6QUISB_rsOWlw=="],"X-Amzn-Trace-Id":["Root=1-683a7e91-7e10636820ca6e5449987b27"],"X-Forwarded-For":["104.28.48.213, 3.172.27.18"],"X-Forwarded-Port":["443"],"X-Forwarded-Proto":["https"]},"queryStringParameters":null,"multiValueQueryStringParameters":null,"pathParameters":null,"stageVariables":null,"requestContext":{"resourceId":"1n92nh","resourcePath":"/save-submission","httpMethod":"POST","extendedRequestId":"Lai20HkIPHcEDIw=","requestTime":"31/May/2025:03:59:13 +0000","path":"/prod/save-submission","accountId":"975050048887","protocol":"HTTP/1.1","stage":"prod","domainPrefix":"o7d0i4to5a","requestTimeEpoch":1748663953698,"requestId":"813e7443-d5f6-45ff-9060-272d5536dc13","identity":{"cognitoIdentityPoolId":null,"accountId":null,"cognitoIdentityId":null,"caller":null,"sourceIp":"104.28.48.213","principalOrgId":null,"accessKey":null,"cognitoAuthenticationType":null,"cognitoAuthenticationProvider":null,"userArn":null,"userAgent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15","user":null},"domainName":"o7d0i4to5a.execute-api.us-west-2.amazonaws.com","deploymentId":"83bgxq","apiId":"o7d0i4to5a"},"body":"{\"email\":\"gbhbyu@gmail.com\",\"propertyTitle\":\"DummyTester\",\"listingDescription\":\"yooooaooa\",\"addressOfProperty\":\"ur mom\",\"optionalNotes\":\"oogabooga\",\"objectKey\":\"1748663920512-5nvr6q-Archive.zip\"}","isBase64Encoded":false}
2025-05-30T21:59:13.711-06:00
2025-05-31T03:59:13.711Z	5f2d3fc3-3374-4c9d-9d3b-350d6a38f467	INFO	Path: /save-submission

2025-05-31T03:59:13.711Z 5f2d3fc3-3374-4c9d-9d3b-350d6a38f467 INFO Path: /save-submission
2025-05-30T21:59:13.875-06:00
2025-05-31T03:59:13.875Z	5f2d3fc3-3374-4c9d-9d3b-350d6a38f467	ERROR	Error handling request: ValidationException: One or more parameter values were invalid: Missing the key id in the item
    at throwDefaultError (/var/runtime/node_modules/@aws-sdk/node_modules/@smithy/smithy-client/dist-cjs/index.js:867:20)
    at /var/runtime/node_modules/@aws-sdk/node_modules/@smithy/smithy-client/dist-cjs/index.js:876:5
    at de_CommandError (/var/runtime/node_modules/@aws-sdk/client-dynamodb/dist-cjs/index.js:2298:14)
    at process.processTicksAndRejections (node:internal/process/task_queues:95:5)
    at async /var/runtime/node_modules/@aws-sdk/node_modules/@smithy/middleware-serde/dist-cjs/index.js:35:20
    at async /var/runtime/node_modules/@aws-sdk/lib-dynamodb/dist-cjs/index.js:174:30
    at async /var/runtime/node_modules/@aws-sdk/node_modules/@smithy/core/dist-cjs/index.js:167:18
    at async /var/runtime/node_modules/@aws-sdk/node_modules/@smithy/middleware-retry/dist-cjs/index.js:320:38
    at async /var/runtime/node_modules/@aws-sdk/middleware-logger/dist-cjs/index.js:33:22
    at async exports.handler (/var/task/index.js:234:7) {
  '$fault': 'client',
  '$metadata': {
    httpStatusCode: 400,
    requestId: 'MA1P55UVPKRU9U6P0N1S8MP9FFVV4KQNSO5AEMVJF66Q9ASUAAJG',
    extendedRequestId: undefined,
    cfId: undefined,
    attempts: 1,
    totalRetryDelay: 0
  },
  __type: 'com.amazon.coral.validate#ValidationException'
}

2025-05-31T03:59:13.875Z 5f2d3fc3-3374-4c9d-9d3b-350d6a38f467 ERROR Error handling request: ValidationException: One or more parameter values were invalid: Missing the key id in the item at throwDefaultError (/var/runtime/node_modules/@aws-sdk/node_modules/@smithy/smithy-client/dist-cjs/index.js:867:20) at /var/runtime/node_modules/@aws-sdk/node_modules/@smithy/smithy-client/dist-cjs/index.js:876:5 at de_CommandError (/var/runtime/node_modules/@aws-sdk/client-dynamodb/dist-cjs/index.js:2298:14) at process.processTicksAndRejections (node:internal/process/task_queues:95:5) at async /var/runtime/node_modules/@aws-sdk/node_modules/@smithy/middleware-serde/dist-cjs/index.js:35:20 at async /var/runtime/node_modules/@aws-sdk/lib-dynamodb/dist-cjs/index.js:174:30 at async /var/runtime/node_modules/@aws-sdk/node_modules/@smithy/core/dist-cjs/index.js:167:18 at async /var/runtime/node_modules/@aws-sdk/node_modules/@smithy/middleware-retry/dist-cjs/index.js:320:38 at async /var/runtime/node_modules/@aws-sdk/middleware-logger/dist-cjs/index.js:33:22 at async exports.handler (/var/task/index.js:234:7) { '$fault': 'client', '$metadata': { httpStatusCode: 400, requestId: 'MA1P55UVPKRU9U6P0N1S8MP9FFVV4KQNSO5AEMVJF66Q9ASUAAJG', extendedRequestId: undefined, cfId: undefined, attempts: 1, totalRetryDelay: 0 }, __type: 'com.amazon.coral.validate#ValidationException' }
2025-05-30T21:59:13.953-06:00
END RequestId: 5f2d3fc3-3374-4c9d-9d3b-350d6a38f467

END RequestId: 5f2d3fc3-3374-4c9d-9d3b-350d6a38f467
2025-05-30T21:59:13.953-06:00
REPORT RequestId: 5f2d3fc3-3374-4c9d-9d3b-350d6a38f467	Duration: 241.92 ms	Billed Duration: 242 ms	Memory Size: 128 MB	Max Memory Used: 91 MB	

REPORT RequestId: 5f2d3fc3-3374-4c9d-9d3b-350d6a38f467 Duration: 241.92 ms Billed Duration: 242 ms Memory Size: 128 MB Max Memory Used: 91 MB
No newer events at this moment. 
Auto retry paused.
 
Resume
 
33 events loaded


And my web dev logs showed this:

[Log] DOM Content Loaded - Initializing popup functionality (script.js, line 1228)
[Log] Found popup element: –  (script.js, line 1232)
<div id="addPathPopup" class="popup hidden">…</div>

<div id="addPathPopup" class="popup hidden">…</div>
[Log] Found add path button (script.js, line 1240)
[Log] Setting up file upload handlers (script.js, line 1255)
[Log] %cLumaSplatsThree git version #43db0c3 (luma-web.module.js, line 72)
[Log] %cDecoder: worker starting. (luma-web.module.js, line 72)
[Log] %cDecoder ready. (luma-web.module.js, line 72)
[Log] %cSorter: Worker starting. (luma-web.module.js, line 69)
[Log] %cSorter ready. (luma-web.module.js, line 69)
[Error] Failed to load resource: the server responded with a status of 404 () (favicon.ico, line 0)
[Log] Execution ARN: – "arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline:execution-a555004a-0b81-4ae8-8af0-bf76552ae301" (script.js, line 1622)
[Log] Multipart upload started: – Object (script.js, line 835)
Object
[Log] Uploaded part #1: 64.70% done (script.js, line 855)
[Log] Uploaded part #2: 100.00% done (script.js, line 855)
[Log] Multipart upload completed! (script.js, line 862)
[Error] Failed to load resource: the server responded with a status of 500 () (save-submission, line 0)