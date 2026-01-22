# Prompt for New Chat - Litchi Automation Completion

Copy and paste this into a new Composer chat:

---

I'm continuing work on the Litchi automation feature. Please read `LITCHI_AUTOMATION_HANDOFF.md` for complete context, then complete the remaining work.

## Current Status
- **Branch**: `agent-49231687-litchi-connection-fix`
- **Backend**: ✅ Complete and deployed (Lambda worker, API, Step Functions)
- **Frontend**: ✅ Complete and integrated (hook, UI components)
- **Testing**: ⚠️ End-to-end verification incomplete

## What I Need You To Do

1. **Read the handoff document** (`LITCHI_AUTOMATION_HANDOFF.md`) to understand the full context

2. **Complete end-to-end testing**:
   - Use test account: `hello@spcprt.com` (password available if needed)
   - Test the full flow: Create project → Optimize paths → Click "Send to Litchi" → Verify uploads complete
   - Check Step Functions executions and worker logs
   - Verify projects appear in Litchi Hub

3. **Fix any issues discovered**:
   - If uploads don't complete, debug and fix
   - If status doesn't update, fix polling/logic
   - If errors occur, improve error handling

4. **Test edge cases**:
   - Invalid credentials
   - Network failures
   - Large projects (10+ batteries)
   - 2FA flow (if possible)

5. **Once everything works**:
   - Run full test suite
   - Update documentation if needed
   - Prepare for merge to `development` branch

## Test Credentials
- **Spaceport**: `hello@spcprt.com` / [ask if needed]
- **Litchi**: `hello@spcprt.com` / `vupwob-jamVub-4cakhy`

## Key Files
- Backend: `infrastructure/spaceport_cdk/lambda/litchi_worker/lambda_function.py`
- Frontend: `web/components/NewProjectModal.tsx` (lines 1450-1515)
- Hook: `web/hooks/useLitchiAutomation.ts`

## Important Notes
- Worker uses `--single-process` mode (may have V8 issues, monitor)
- Session cookies stored in DynamoDB for reuse
- Random jitter delays (12-25s) between uploads
- Mission naming: `${projectTitle} - ${n}`

Start by reading `LITCHI_AUTOMATION_HANDOFF.md` for complete details, then proceed with testing and fixes.

---
