import json
import os
from urllib.parse import urlparse

import boto3
from botocore.config import Config


s3 = boto3.client("s3", config=Config(signature_version="s3v4"))


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
        },
        "body": json.dumps(body),
    }


def _parse_s3_url(raw_url):
    if not isinstance(raw_url, str) or not raw_url.strip():
        raise ValueError("Artifact URL must be a non-empty string.")

    parsed = urlparse(raw_url.strip())

    if parsed.scheme == "s3":
        bucket = parsed.netloc
        key = parsed.path.lstrip("/")
        if bucket and key:
            return bucket, key

    if parsed.scheme == "https" and parsed.netloc.endswith(".s3.amazonaws.com"):
        bucket = parsed.netloc[: -len(".s3.amazonaws.com")]
        key = parsed.path.lstrip("/")
        if bucket and key:
            return bucket, key

    if parsed.scheme == "https" and ".s3.us-west-2.amazonaws.com" in parsed.netloc:
        bucket = parsed.netloc.split(".s3.us-west-2.amazonaws.com", 1)[0]
        key = parsed.path.lstrip("/")
        if bucket and key:
            return bucket, key

    raise ValueError(f"Unsupported artifact URL: {raw_url!r}")


def lambda_handler(event, context):
    try:
        method = event.get("httpMethod", "POST")
        if method == "OPTIONS":
            return _response(200, {"ok": True})
        if method != "POST":
            return _response(405, {"error": "Method not allowed"})

        body = json.loads(event.get("body") or "{}")
        raw_urls = body.get("urls")
        if not isinstance(raw_urls, list) or not raw_urls:
            return _response(400, {"error": "Request body must include a non-empty urls array."})
        if len(raw_urls) > 10:
            return _response(400, {"error": "At most 10 artifact URLs may be requested at once."})

        ml_bucket = os.environ["ML_BUCKET"]
        artifacts = []

        for raw_url in raw_urls:
            bucket, key = _parse_s3_url(raw_url)
            if bucket != ml_bucket:
                return _response(
                    403,
                    {
                        "error": (
                            f"Artifact bucket {bucket!r} is not allowed for this environment. "
                            f"Expected {ml_bucket!r}."
                        )
                    },
                )

            signed_url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=900,
            )
            artifacts.append({"sourceUrl": raw_url, "signedUrl": signed_url})

        return _response(200, {"artifacts": artifacts})

    except ValueError as error:
        return _response(400, {"error": str(error)})
    except Exception as error:
        print(f"Error presigning ML artifact URL: {error}")
        return _response(500, {"error": f"Internal server error: {error}"})
