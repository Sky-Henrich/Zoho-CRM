# bd_sync_active_members — Session Summary

Tracks the work done on `functions/standalone/bd_sync_active_members.dg`, the Deluge function that syncs Brilliant Directories (BD) member/subscription webhooks into Zoho CRM (Leads, Contacts, Accounts, Deals). All commits are on branch `claude/kind-sagan-gx43vg`.

## What we accomplished

**Reliability fixes**
- Added response validation to `zoho.crm.updateRecord`/`createRecord` calls. Zoho's success response has no `"status"` key (just the record's fields); only errors carry `"status":"error"`. The function used to log success unconditionally, masking real rejections (e.g. a bad picklist value).
- Split `Stage` into its own separate update call. Zoho rejects an entire `updateRecord` call if `Stage` is included while the Deal is mid-Blueprint — this was silently blocking `Current_Plan` and every other field bundled into the same call.
- Implemented the Blueprint Transition REST API (GET available transitions, PUT to execute one) so Stage changes on a Blueprint-governed Deal (Closed Won, Sales Outreach, etc.) actually go through, instead of the plain field write Zoho rejects. Requires a one-time Connection (`bd_sync_blueprint_connection`) set up in Zoho — already done.
- Fixed Contact lookups to search by `BD_Member_ID` first everywhere (previously only Email/Phone), which was causing duplicate Contacts whenever a member edited their email or phone in BD.
- Fixed a critical regression: a stale-Lead cleanup step was deleting Leads that correctly failed the Claimable conversion gate (see below), assuming any Lead found in that branch must be a stale duplicate. Now gated on whether conversion actually happened.

**Field sync fixes**
- `Verified_Member`: webhook body parsing of `user[verified]` proved unreliable on real payloads; switched to reading it from BD's live user API (`u.get("verified")`) instead.
- `BD_Profile_URL`: fixed URL construction (handles a leading `/` in BD's filename) and extended syncing to Deals and Accounts (was previously Leads/Contacts only).
- `Lead_Source = "IGP"`: mapped consistently across Leads, Contacts, and Deals (Accounts doesn't have this field).
- `Current_Plan`/`Top_Category` now sync onto a Lead even when it's correctly held back from converting to a Deal — previously the Lead-tagging step never touched these fields at all, so a Lead kept showing a stale plan name after BD had already moved on.
- Recognized `member[user_id]` (used by BD's `subscription_updated` webhook) as another valid source for the BD member ID.

**Business logic — Deal Stage**
- Closed Won now requires all three: amount paid > 0, `Current_Plan` is one of the ten Verificado/Impulso tiers, and `Trial_Plan` is empty. Sales Outreach is the fallback stage whenever any condition isn't met.
- `Trial_Plan` / `Subscription_Start_Date` are now plan-type-aware:
  - Listing plans (Visit/Relocate/Stay/Experience/Live Listing): both stay empty — not a trial.
  - Verificado/Impulso at $0: `Trial_Plan = "Alumni Free Trial"`, `Subscription_Start_Date` synced from the plan's start date.
  - Verificado/Impulso, paid: `Trial_Plan` cleared, `Subscription_Start_Date` tracked normally, Stage → Closed Won.
- "Claimable" plans route to Leads only, never touching Deals — a lapsed listing isn't a live sales opportunity.
- Converting a Claimable-origin Lead to a Deal now requires **both**: the plan just moved from Claimable to a Listing plan, **and** `Verified_Member = YES`. Either missing → stays a Lead (tagged with latest info, not converted).
- Reverted an earlier, incorrect attempt at inferring a "Free Trial" **Stage** automatically from `amount == 0` — that conflated a trial *plan* (a Trial_Plan field value) with a pipeline *stage*, and was overriding "Sales Outreach" when it shouldn't have.

**Repo hygiene**
- Found and removed a duplicate, independently-drifting copy of this script (`function/standalone/bd_sync_active_members1`) that had picked up its own fixes (ported the useful one — the Contact `BD_Member_ID` lookup — into this file). `functions/standalone/bd_sync_active_members.dg` is now the single source of truth.

## Current state

- All code lives in this repo on `claude/kind-sagan-gx43vg`; there is **no automated deployment** — the live version running in Zoho CRM is whatever was last manually copy-pasted into the Deluge function editor and saved.
- Testing has been done by POSTing webhook-style form payloads to the function's REST API execution endpoint (via Postman or similar) and inspecting the returned `resultLog` plus the resulting CRM records.
- The most recent commit (`0498227`) — syncing `Current_Plan`/`Top_Category` onto a Lead even when conversion is blocked — has not yet been confirmed with a fresh test.

## Next steps

1. **Verify the latest fix.** Re-run the Claimable → Listing (not yet verified) test payload and confirm the Lead now shows the new `Current_Plan` while still correctly staying unconverted.
2. **Decide on split-event verification.** The "was Claimable" detection currently only reliably fires when the plan change and the verification change arrive in the *same* webhook event. If BD/admins sometimes do these as two separate saves, the gate needs to persist "this Lead came from Claimable" on the record itself rather than relying on a single event's `old_user[subscription_name]`.
3. **Confirm deployment.** Make sure the version in Zoho's function editor matches the latest commit on `claude/kind-sagan-gx43vg` before relying on this in production.
4. **Not in scope this session:** the CSV-import lookup function (enriches imported Leads with `BD_Member_ID`/`BD_Profile_URL`/`Verified_Member` from BD) already exists separately and was not modified. The `Trial_End_Date`/`Renewal_Due_Date` sync from the `subscription_updated` webhook was explicitly dropped per your instruction and is not implemented.
5. **Possible follow-up audit:** the Individual/Community branch's Lead handling wasn't reviewed for the same kind of `Current_Plan` sync gap found in the Claimable path — worth a look if similar staleness is seen there.
