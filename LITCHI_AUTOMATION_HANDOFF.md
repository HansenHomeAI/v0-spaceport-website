# Litchi Automation Feature - Handoff Document

**Date**: 2026-01-22  
**Branch**: `agent-49231687-litchi-connection-fix`  
**Status**: Backend operational, frontend integrated, end-to-end testing incomplete

---

## 🎯 Feature Overview

Automated upload of drone flight paths (battery segments) to Litchi Mission Hub. Users connect their Litchi account once, then click "Send to Flight Controller" to automatically create projects and upload CSV files for all battery segments.

---

## ✅ What's Been Accomplished

### Backend (100% Complete)
1. **Lambda Worker** (`infrastructure/spaceport_cdk/lambda/litchi_worker/`)
   - ✅ Containerized with Playwright + Chromium
   - ✅ Handles Litchi login modal correctly
   - ✅ Uploads CSV files via hidden import buttons
   - ✅ Fixed GPU crashes with software rendering flags
   - ✅ Current launch args: `--no-zygote`, `--single-process`, `--use-gl=swiftshader`
   - ✅ Environment vars: `LIBGL_ALWAYS_SOFTWARE=1`, `GALLIUM_DRIVER=llvmpipe`

2. **Lambda API** (`infrastructure/spaceport_cdk/lambda/litchi_api/`)
   - ✅ Fixed Decimal serialization errors
   - ✅ Status, connect, upload endpoints working
   - ✅ CORS configured
   - ✅ Cognito authorizer integrated

3. **Step Functions** (`infrastructure/spaceport_cdk/spaceport_cdk/auth_stack.py`)
   - ✅ Orchestrates uploads with jitter delays (12-25 seconds)
   - ✅ Handles retries and error reporting

4. **DynamoDB**
   - ✅ Credentials table with KMS encryption
   - ✅ Session storage for cookie persistence

### Frontend (100% Complete)
1. **Hook** (`web/hooks/useLitchiAutomation.ts`)
   - ✅ Centralized API calls
   - ✅ Status polling (15s interval)
   - ✅ Fallback API base handling
   - ✅ Error handling and retries

2. **UI Integration** (`web/components/NewProjectModal.tsx`)
   - ✅ "Send to Litchi" button integrated into project modal
   - ✅ Inline connection form (email/password/2FA)
   - ✅ "Download manually" fallback button
   - ✅ Progress indicators and error messages
   - ✅ Auto-generates mission names: `${projectTitle} - ${n}`

3. **Standalone Component** (`web/components/LitchiMissionControl.tsx`)
   - ✅ Uses same hook for synced state
   - ✅ Dashboard card for manual uploads

---

## 🔧 Current Technical State

### Worker Launch Configuration
```python
# infrastructure/spaceport_cdk/lambda/litchi_worker/lambda_function.py
os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")
os.environ.setdefault("GALLIUM_DRIVER", "llvmpipe")

browser = await playwright.chromium.launch(
    headless=True,
    args=[
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--no-zygote",
        "--single-process",
        "--use-gl=swiftshader",
        "--ignore-gpu-blocklist",
    ],
)
context = await browser.new_context(
    user_agent=random.choice(USER_AGENTS),
    viewport=None,  # Prevents device emulation crashes
    locale="en-US",
)
```

### API Endpoints
- **Status**: `GET /litchi/status` - Returns connection status, progress, logs
- **Connect**: `POST /litchi/connect` - Initiates login flow
- **Upload**: `POST /litchi/upload` - Starts Step Functions upload job

### Step Functions Delay Logic
- Random jitter: `random.randint(12, 25)` seconds between uploads
- Prevents rate limiting while appearing human-like

---

## 🧪 Test Credentials

### Spaceport Account (for UI testing)
- **Email**: `hello@spcprt.com`
- **Password**: [User has this - ask if needed]
- **Cognito Pool**: `us-west-2_a2jf3ldGV` (Spaceport-Users-v2)
- **Client ID**: `3ctkuqu98pmug5k5kgc119sq67`

### Litchi Account (for automation testing)
- **Email**: `hello@spcprt.com`
- **Password**: `vupwob-jamVub-4cakhy`
- **Account Name**: Spaceport AI

---

## ⚠️ Known Issues & Testing Status

### ✅ Working
- ✅ Worker can launch browser (no more GPU crashes)
- ✅ Login flow handles modal correctly
- ✅ API endpoints respond correctly
- ✅ Frontend UI integrated and functional
- ✅ Session persistence (cookies stored in DynamoDB)

### 🔄 Needs Verification
- ⚠️ **End-to-end upload flow**: UI shows "uploading" but backend logs unclear
- ⚠️ **Step Functions execution**: Need to verify uploads actually complete
- ⚠️ **Mission naming**: Verify `${projectTitle} - ${n}` format works
- ⚠️ **Error handling**: Test failure scenarios (invalid credentials, network errors)
- ⚠️ **2FA flow**: Not yet tested with 2FA-enabled accounts

### 🐛 Potential Issues
- **Upload not completing**: UI shows "uploading" but status doesn't update
  - May need to check Step Functions execution logs
  - May need to verify CSV generation before upload
- **API URL fallback**: Frontend has fallback logic but may not be triggering correctly

---

## 📋 Next Steps (Priority Order)

### 1. End-to-End Testing (CRITICAL)
**Goal**: Verify complete flow from UI click → Litchi Hub

**Steps**:
1. Log into preview site with `hello@spcprt.com`
2. Create/open a project with optimized flight paths
3. Click "Send to Litchi" button
4. Monitor:
   - Step Functions execution (check CloudWatch)
   - Worker logs for each battery upload
   - Litchi Hub to verify projects appear
   - UI status updates

**Scripts Available**:
- `scripts/run_litchi_ui_flow_tmp.mjs` - Full UI automation
- `scripts/run_litchi_connect_flow_tmp.mjs` - Direct API connect test
- `scripts/run_litchi_status_debug_tmp.mjs` - Status check

### 2. Fix Upload Completion Detection
**If uploads aren't completing**:
- Check Step Functions execution logs
- Verify CSV generation happens before upload call
- Check if `handleSendToLitchi` waits for optimization
- Verify status polling updates correctly

### 3. Error Handling & Edge Cases
- Test with invalid Litchi credentials
- Test with 2FA-enabled account
- Test network failure scenarios
- Test with 0 battery segments
- Test with very large projects (10+ batteries)

### 4. Performance & Rate Limiting
- Verify jitter delays prevent rate limiting
- Test with maximum battery count
- Monitor Lambda execution time (15min limit)

---

## 📁 Key Files

### Backend
- `infrastructure/spaceport_cdk/lambda/litchi_worker/lambda_function.py` - Browser automation
- `infrastructure/spaceport_cdk/lambda/litchi_worker/Dockerfile` - Container image
- `infrastructure/spaceport_cdk/lambda/litchi_api/lambda_function.py` - API endpoints
- `infrastructure/spaceport_cdk/spaceport_cdk/auth_stack.py` - Step Functions definition

### Frontend
- `web/hooks/useLitchiAutomation.ts` - Centralized hook
- `web/components/NewProjectModal.tsx` - Integrated UI (lines 1450-1515)
- `web/components/LitchiMissionControl.tsx` - Standalone component
- `web/app/api-config.ts` - API URL configuration

### Testing
- `scripts/run_litchi_ui_flow_tmp.mjs` - Full UI test
- `scripts/run_litchi_connect_flow_tmp.mjs` - Connect test
- `scripts/run_litchi_status_debug_tmp.mjs` - Status check

---

## 🔍 Debugging Commands

### Check Worker Logs
```bash
aws logs tail /aws/lambda/Spaceport-LitchiWorkerFunction-staging --follow --region us-west-2
```

### Check API Logs
```bash
aws logs tail /aws/lambda/Spaceport-LitchiApiFunction-staging --follow --region us-west-2
```

### Check Step Functions
```bash
# Get state machine ARN
aws cloudformation describe-stacks --stack-name SpaceportAuthStagingStack --region us-west-2 --query 'Stacks[0].Outputs[?OutputKey==`LitchiStateMachineArn`].OutputValue' --output text

# List recent executions
aws stepfunctions list-executions --state-machine-arn <ARN> --max-results 10 --region us-west-2
```

### Test API Directly
```bash
# Get token first (from browser localStorage or Amplify)
curl -X GET "https://4ambcdgywa.execute-api.us-west-2.amazonaws.com/prod/litchi/status" \
  -H "Authorization: Bearer <TOKEN>"
```

---

## 🚀 Deployment Status

### Current Branch
- **Branch**: `agent-49231687-litchi-connection-fix`
- **Preview URL**: `https://agent-49231687-litchi-connec.v0-spaceport-website-preview2.pages.dev`
- **API Endpoint**: `https://4ambcdgywa.execute-api.us-west-2.amazonaws.com/prod/`

### Recent Commits
- `68ef4a7` - fix: tune litchi worker launch for lambda
- `5fd7f72` - fix: force software rendering for litchi worker
- `02f7677` - fix: harden litchi worker chromium launch
- `716ce24` - fix: coerce decimals in litchi api

### Deployment Status
- ✅ CDK deployment successful
- ✅ Lambda functions deployed
- ✅ Step Functions deployed
- ✅ API Gateway configured
- ⚠️ End-to-end testing incomplete

---

## 💡 Important Notes

1. **Session Persistence**: Litchi cookies are stored in DynamoDB and reused for subsequent uploads (avoids repeated logins)

2. **Rate Limiting**: Uses random jitter (12-25s) between uploads to appear human-like and avoid bans

3. **Mission Naming**: Format is `${projectTitle} - ${n}` (e.g., "My Property - 1", "My Property - 2")

4. **Error Recovery**: Frontend has fallback API base logic, but may need refinement

5. **2FA Support**: UI supports 2FA entry, but flow not fully tested

6. **Lambda Limits**: Worker has 15-minute execution limit, 2048MB memory, containerized runtime

---

## 🎯 Success Criteria

Feature is production-ready when:
- ✅ User can connect Litchi account via UI
- ✅ User can click "Send to Litchi" and see progress
- ✅ All battery segments upload successfully to Litchi Hub
- ✅ Projects appear in Litchi Hub with correct names
- ✅ Error messages are clear and actionable
- ✅ 2FA flow works (if applicable)
- ✅ Rate limiting doesn't trigger bans

---

## 📞 If You Need Help

1. **Check CloudWatch logs first** - Most issues show up there
2. **Verify Step Functions execution** - Upload orchestration happens there
3. **Test API endpoints directly** - Isolate frontend vs backend issues
4. **Check browser automation** - Worker logs show Playwright actions
5. **Review STATE.md** - May have additional context

---

**Last Updated**: 2026-01-22  
**Next Action**: Complete end-to-end testing with real credentials
