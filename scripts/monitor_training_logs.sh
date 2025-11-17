#!/bin/bash
# Monitor live CloudWatch logs for SageMaker training job

JOB_NAME="ml-job-20251117-105839-3dgs-tes-3dgs"
REGION="us-west-2"
LOG_GROUP="/aws/sagemaker/TrainingJobs"

echo "🔍 Finding log stream for job: $JOB_NAME"
echo ""

# Find the log stream
LOG_STREAM=$(aws logs describe-log-streams \
  --log-group-name "$LOG_GROUP" \
  --log-stream-name-prefix "$JOB_NAME" \
  --region "$REGION" \
  --max-items 10 \
  --query 'logStreams[0].logStreamName' \
  --output text 2>/dev/null)

if [ "$LOG_STREAM" == "None" ] || [ -z "$LOG_STREAM" ]; then
  echo "⏳ Log stream not found yet. Job may still be downloading data."
  echo "   Waiting for logs to appear..."
  echo ""
  
  # Poll until log stream appears
  for i in {1..30}; do
    sleep 5
    LOG_STREAM=$(aws logs describe-log-streams \
      --log-group-name "$LOG_GROUP" \
      --log-stream-name-prefix "$JOB_NAME" \
      --region "$REGION" \
      --order-by LastEventTime \
      --descending \
      --max-items 1 \
      --query 'logStreams[0].logStreamName' \
      --output text 2>/dev/null)
    
    if [ "$LOG_STREAM" != "None" ] && [ -n "$LOG_STREAM" ]; then
      echo "✅ Log stream found: $LOG_STREAM"
      break
    fi
    echo "   Still waiting... ($i/30)"
  done
  
  if [ "$LOG_STREAM" == "None" ] || [ -z "$LOG_STREAM" ]; then
    echo "❌ Log stream not found after waiting. Check job status manually."
    exit 1
  fi
fi

echo "📊 Streaming logs from: $LOG_STREAM"
echo "   (Press Ctrl+C to stop)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if aws logs tail is available (newer AWS CLI versions)
if aws logs tail --help &>/dev/null; then
  # Use tail command for live streaming
  aws logs tail "$LOG_GROUP" \
    --log-stream-names "$LOG_STREAM" \
    --region "$REGION" \
    --follow \
    --format short
else
  # Fallback: Poll and display new logs
  LAST_TOKEN=""
  while true; do
    if [ -z "$LAST_TOKEN" ]; then
      # First call - get recent logs
      OUTPUT=$(aws logs get-log-events \
        --log-group-name "$LOG_GROUP" \
        --log-stream-name "$LOG_STREAM" \
        --region "$REGION" \
        --limit 10 \
        --start-from-head false \
        --query 'events[*].[timestamp,message]' \
        --output text 2>/dev/null)
      
      if [ -n "$OUTPUT" ]; then
        echo "$OUTPUT" | while IFS=$'\t' read -r timestamp message; do
          echo "[$(date -r $((timestamp/1000)) '+%H:%M:%S')] $message"
        done
        LAST_TOKEN=$(aws logs get-log-events \
          --log-group-name "$LOG_GROUP" \
          --log-stream-name "$LOG_STREAM" \
          --region "$REGION" \
          --limit 1 \
          --start-from-head false \
          --query 'nextForwardToken' \
          --output text 2>/dev/null)
      fi
    else
      # Subsequent calls - get new logs
      OUTPUT=$(aws logs get-log-events \
        --log-group-name "$LOG_GROUP" \
        --log-stream-name "$LOG_STREAM" \
        --region "$REGION" \
        --next-token "$LAST_TOKEN" \
        --query 'events[*].[timestamp,message]' \
        --output text 2>/dev/null)
      
      if [ -n "$OUTPUT" ]; then
        echo "$OUTPUT" | while IFS=$'\t' read -r timestamp message; do
          echo "[$(date -r $((timestamp/1000)) '+%H:%M:%S')] $message"
        done
      fi
      
      LAST_TOKEN=$(aws logs get-log-events \
        --log-group-name "$LOG_GROUP" \
        --log-stream-name "$LOG_STREAM" \
        --region "$REGION" \
        --next-token "$LAST_TOKEN" \
        --limit 1 \
        --query 'nextForwardToken' \
        --output text 2>/dev/null)
    fi
    
    sleep 2
  done
fi

