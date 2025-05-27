const { S3Client, CreateMultipartUploadCommand, UploadPartCommand, CompleteMultipartUploadCommand } = require("@aws-sdk/client-s3");
const { getSignedUrl } = require("@aws-sdk/s3-request-presigner");
const { DynamoDBClient } = require("@aws-sdk/client-dynamodb");
const { DynamoDBDocumentClient, PutCommand } = require("@aws-sdk/lib-dynamodb");
const { SESClient, SendEmailCommand } = require("@aws-sdk/client-ses");

// Initialize clients
const s3Client = new S3Client({ region: "us-west-2" });
const dynamoClient = new DynamoDBClient({ region: "us-west-2" });
const docClient = DynamoDBDocumentClient.from(dynamoClient);
const sesClient = new SESClient({ region: "us-west-2" });

const BUCKET_NAME = process.env.BUCKET_NAME; // Use environment variable from CDK
const METADATA_TABLE_NAME = process.env.METADATA_TABLE_NAME; // Use environment variable from CDK

// Helper function to send an email via SES
async function sendEmailNotification(toAddress, subject, bodyText) {
  const params = {
    Destination: { ToAddresses: [toAddress] },
    Message: {
      Subject: { Data: subject },
      Body: { Text: { Data: bodyText } },
    },
    Source: "hello@hansenhome.ai", // Must be a verified sender in SES
  };
  const command = new SendEmailCommand(params);
  return sesClient.send(command);
}

exports.handler = async (event) => {
  console.log("Event received:", JSON.stringify(event));

  // Common CORS headers for all responses
  const corsHeaders = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };

  // Handle OPTIONS preflight
  if (event.httpMethod === "OPTIONS") {
    return {
      statusCode: 200,
      headers: corsHeaders,
      body: JSON.stringify({ message: "OPTIONS request" }),
    };
  }

  // Attempt to parse JSON body
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

  const path = event.resource || event.path; // Adjust depending on how your API Gateway is set up
  console.log("Path:", path);

  try {
    // ----------------------------------------------------------------------
    // 1) START MULTIPART UPLOAD
    //    POST /start-multipart-upload
    // ----------------------------------------------------------------------
    if (path === "/start-multipart-upload") {
      // e.g. body = { fileName, fileType, ... }
      const { fileName } = body;
      if (!fileName) {
        throw new Error("Missing fileName");
      }

      // Generate a random + timestamp-based key
      const randomKeyPart = Math.random().toString(36).substring(2, 8);
      const finalKey = `${Date.now()}-${randomKeyPart}-${fileName}`;

      const s3Params = {
        Bucket: BUCKET_NAME,
        Key: finalKey,
        ACL: "bucket-owner-full-control",
      };

      // Initiate the multipart upload
      const command = new CreateMultipartUploadCommand(s3Params);
      const createResp = await s3Client.send(command);
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

    // ----------------------------------------------------------------------
    // 2) GET PRESIGNED URL FOR PART
    //    POST /get-presigned-url
    // ----------------------------------------------------------------------
    if (path === "/get-presigned-url") {
      // e.g. body = { uploadId, bucketName, objectKey, partNumber }
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

      // Generate a presigned URL for the uploadPart operation
      const command = new UploadPartCommand(partParams);
      const url = await getSignedUrl(s3Client, command, { expiresIn: 3600 });
      console.log("Presigned URL for part:", partNumber, url);

      return {
        statusCode: 200,
        headers: corsHeaders,
        body: JSON.stringify({ url, partNumber }),
      };
    }

    // ----------------------------------------------------------------------
    // 3) COMPLETE MULTIPART UPLOAD
    //    POST /complete-multipart-upload
    // ----------------------------------------------------------------------
    if (path === "/complete-multipart-upload") {
      // e.g. body = { uploadId, bucketName, objectKey, parts: [{ ETag, PartNumber }, ...] }
      const { uploadId, bucketName, objectKey, parts } = body;
      if (!uploadId || !bucketName || !objectKey || !parts) {
        throw new Error("Missing one or more required fields to complete upload.");
      }

      // The "Parts" array must be sorted by PartNumber ascending
      const sortedParts = parts.sort((a, b) => a.PartNumber - b.PartNumber);

      const completeParams = {
        Bucket: bucketName,
        Key: objectKey,
        UploadId: uploadId,
        MultipartUpload: {
          Parts: sortedParts.map(p => ({
            ETag: p.ETag,
            PartNumber: p.PartNumber,
          })),
        },
      };

      const command = new CompleteMultipartUploadCommand(completeParams);
      const completionResp = await s3Client.send(command);
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

    // ----------------------------------------------------------------------
    // OPTIONAL: The old single-part approach (if still needed)
    // POST /generate-presigned-url
    // ----------------------------------------------------------------------
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

      const params = {
        Bucket: BUCKET_NAME,
        Key: finalKey,
        ContentType: fileType,
      };
      
      const { PutObjectCommand } = require("@aws-sdk/client-s3");
      const command = new PutObjectCommand(params);
      const presignedURL = await getSignedUrl(s3Client, command, { expiresIn: 300 });
      
      return {
        statusCode: 200,
        headers: corsHeaders,
        body: JSON.stringify({ url: presignedURL }),
      };
    }

    // ----------------------------------------------------------------------
    // 4) SAVE SUBMISSION METADATA (& Send Email Notifications)
    //     POST /save-submission
    // ----------------------------------------------------------------------
    if (path === "/save-submission") {
      // Expected body fields:
      // { email, propertyTitle, listingDescription, addressOfProperty, optionalNotes, objectKey }
      const { email, propertyTitle, listingDescription, addressOfProperty, optionalNotes, objectKey } = body;
      if (!objectKey || !email || !propertyTitle) {
        throw new Error("Missing required fields: objectKey, email, or propertyTitle");
      }

      // 4a) Save to DynamoDB
      const params = {
        TableName: METADATA_TABLE_NAME,
        Item: {
          SubmissionId: objectKey, // using the unique S3 object key
          Email: email,
          PropertyTitle: propertyTitle,
          ListingDescription: listingDescription,
          Address: addressOfProperty,
          OptionalNotes: optionalNotes || "",
          Timestamp: Date.now()
        }
      };
      
      const command = new PutCommand(params);
      await docClient.send(command);
      console.log("Metadata saved to DynamoDB:", params.Item);

      // 4b) Send email notifications
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

        await Promise.all([
          sendEmailNotification(email, userSubject, userBody),
          sendEmailNotification("hello@hansenhome.ai", adminSubject, adminBody)
        ]);

        console.log("Email notifications sent.");
      } catch (emailErr) {
        console.error("Error sending email notifications:", emailErr);
        // Not throwing here, so we still return a 200 if metadata was saved
      }

      return {
        statusCode: 200,
        headers: corsHeaders,
        body: JSON.stringify({ message: "Submission saved successfully" }),
      };
    }

    // ----------------------------------------------------------------------
    // If none of the above matched, return 404
    // ----------------------------------------------------------------------
    return {
      statusCode: 404,
      headers: corsHeaders,
      body: JSON.stringify({ error: "No matching path" }),
    };

  } catch (err) {
    console.error("Error handling request:", err);
    return {
      statusCode: 500,
      headers: corsHeaders,
      body: JSON.stringify({ error: err.message }),
    };
  }
};
