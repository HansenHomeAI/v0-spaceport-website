const AWS = require('aws-sdk');
const S3 = new AWS.S3();
const dynamoClient = new AWS.DynamoDB.DocumentClient();
const SES = new AWS.SES({ region: "us-west-2" });

const BUCKET_NAME = process.env.BUCKET_NAME;
const METADATA_TABLE_NAME = process.env.METADATA_TABLE_NAME;

/**
 * Handler for file upload requests.
 */
async function sendEmailNotification(toAddress, subject, bodyText) {
  const params = {
    Destination: { ToAddresses: [toAddress] },
    Message: {
      Subject: { Data: subject },
      Body: { Text: { Data: bodyText } },
    },
    Source: "hello@hansenhome.ai",
  };
  return SES.sendEmail(params).promise();
}

exports.handler = async (event) => {
  console.log("Event received:", JSON.stringify(event));

  const corsHeaders = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };

  if (event.httpMethod === "OPTIONS") {
    return {
      statusCode: 200,
      headers: corsHeaders,
      body: JSON.stringify({ message: "OPTIONS request" }),
    };
  }

  let body;
  try {
    body = JSON.parse(event.body || "{}");
  } catch (err) {
    console.error("Error parsing JSON body:", err);
    return {
      statusCode: 400,
      headers: corsHeaders,
      body: JSON.stringify({ error: "Invalid JSON" }),
    };
  }

  const path = event.resource || event.path;
  console.log("Path:", path);

  try {
    if (path === "/start-multipart-upload") {
      const { fileName } = body;
      if (!fileName) {
        throw new Error("Missing fileName");
      }

      const randomKeyPart = Math.random().toString(36).substring(2, 8);
      const finalKey = `${Date.now()}-${randomKeyPart}-${fileName}`;

      const s3Params = {
        Bucket: BUCKET_NAME,
        Key: finalKey,
        ACL: "bucket-owner-full-control",
      };

      const createResp = await S3.createMultipartUpload(s3Params).promise();
      console.log("Multipart upload initiated:", createResp);

      return {
        statusCode: 200,
        headers: corsHeaders,
        body: JSON.stringify({
          uploadId: createResp.UploadId,
          bucketName: createResp.Bucket,
          objectKey: createResp.Key,
        }),
      };
    }

    if (path === "/get-presigned-url") {
      const { uploadId, bucketName, objectKey, partNumber } = body;
      if (!uploadId || !bucketName || !objectKey || !partNumber) {
        throw new Error("Missing uploadId, bucketName, objectKey, or partNumber");
      }

      const partParams = {
        Bucket: bucketName,
        Key: objectKey,
        UploadId: uploadId,
        PartNumber: partNumber,
      };

      const url = await S3.getSignedUrlPromise("uploadPart", partParams);
      console.log("Presigned URL for part:", partNumber, url);

      return {
        statusCode: 200,
        headers: corsHeaders,
        body: JSON.stringify({ url, partNumber }),
      };
    }

    if (path === "/complete-multipart-upload") {
      const { uploadId, bucketName, objectKey, parts } = body;
      if (!uploadId || !bucketName || !objectKey || !parts) {
        throw new Error("Missing one or more required fields to complete upload.");
      }

      const sortedParts = parts.sort((a, b) => a.PartNumber - b.PartNumber);

      const completeParams = {
        Bucket: bucketName,
        Key: objectKey,
        UploadId: uploadId,
        MultipartUpload: { Parts: sortedParts.map(p => ({ ETag: p.ETag, PartNumber: p.PartNumber })) },
      };

      const completionResp = await S3.completeMultipartUpload(completeParams).promise();
      console.log("Multipart upload completed:", completionResp);

      return {
        statusCode: 200,
        headers: corsHeaders,
        body: JSON.stringify({
          message: "Upload complete",
          location: completionResp.Location,
        }),
      };
    }

    if (path === "/generate-presigned-url") {
      const { fileName, fileType } = body;
      if (!fileName || !fileType) {
        return {
          statusCode: 400,
          headers: corsHeaders,
          body: JSON.stringify({ error: "Missing fileName or fileType" }),
        };
      }

      const randomKeyPart = Math.random().toString(36).substring(2, 8);
      const finalKey = `${Date.now()}-${randomKeyPart}-${fileName}`;

      const params = { Bucket: BUCKET_NAME, Key: finalKey, ContentType: fileType, Expires: 300 };
      const presignedURL = await S3.getSignedUrlPromise("putObject", params);
      return {
        statusCode: 200,
        headers: corsHeaders,
        body: JSON.stringify({ url: presignedURL }),
      };
    }

    if (path === "/save-submission") {
      const { email, propertyTitle, listingDescription, addressOfProperty, optionalNotes, objectKey } = body;
      if (!objectKey || !email || !propertyTitle) {
        throw new Error("Missing required fields: objectKey, email, or propertyTitle");
      }

      const dbParams = { TableName: METADATA_TABLE_NAME, Item: { SubmissionId: objectKey, Email: email, PropertyTitle: propertyTitle, ListingDescription: listingDescription, Address: addressOfProperty, OptionalNotes: optionalNotes || "", Timestamp: Date.now() } };
      await dynamoClient.put(dbParams).promise();
      console.log("Metadata saved to DynamoDB:", dbParams.Item);

      try {
        const userSubject = "We've Received Your Drone Photos!";
        const userBody = `Hello,

Thank you for your submission! We have received your photos and will start processing them soon.
Your upload ID is: ${objectKey}

Best,
The Hansen AI Team
`;

        const adminSubject = "New Upload Received";
        const adminBody = `New drone photo submission received:

Email: ${email}
Property Title: ${propertyTitle}
Description: ${listingDescription}
Address: ${addressOfProperty}
Optional Notes: ${optionalNotes}
Upload ID: ${objectKey}

Please process this submission accordingly.`;

        await Promise.all([ sendEmailNotification(email, userSubject, userBody), sendEmailNotification("hello@hansenhome.ai", adminSubject, adminBody) ]);

        console.log("Email notifications sent.");
      } catch (emailErr) {
        console.error("Error sending email notifications:", emailErr);
      }

      return {
        statusCode: 200,
        headers: corsHeaders,
        body: JSON.stringify({ message: "Submission saved successfully" }),
      };
    }

    return { statusCode: 404, headers: corsHeaders, body: JSON.stringify({ error: "No matching path" }) };

  } catch (err) {
    console.error("Error handling request:", err);
    return { statusCode: 500, headers: corsHeaders, body: JSON.stringify({ error: err.message }) };
  }
}; 