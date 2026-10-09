# Zoho-CRM

Code that connects the I Go Panama website (Brilliant Directories, "BD") to Zoho CRM.
Nothing here deploys automatically: each file is copy-pasted into the system it runs in.

| File | Runs in | Paste it into |
|---|---|---|
| `functions/standalone/bd_sync_active_members.dg` | Zoho CRM (Deluge) | Zoho CRM function `bd_sync_active_members` (Deluge editor) |
| `bd/additional_footer_code.html` | Visitors' browsers | BD admin → Additional Footer Code setting |

Edit the file here first, then paste it into the live system, so this repo always
matches what is running. Keep exactly one copy of each file.

## UTM tracking: how the two files work together

1. A visitor opens a tagged link from the monthly UTM link sheet, e.g.
   `igopanama.com/guides?utm_source=instagram&utm_medium=bio&utm_campaign=ind-organic-2026-10`.
2. **Footer code** (the UTM capture script at the bottom of
   `bd/additional_footer_code.html`) saves `utm_source`, `utm_medium`,
   `utm_campaign` and `utm_content` in the `igp_utm` cookie for 30 days. A newer
   tagged visit replaces it (last touch), and values are lowercased.
3. On any page with a form, the footer code fills hidden inputs named exactly
   `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`. **Each BD form that
   should be tracked (join, claim, quote, business enquiry) needs these four hidden
   fields** — the script fills them but does not create them.
4. BD saves the values on the member and sends them in its webhook.
5. **Zoho function** (`UTM_SOURCE_TRACKING` patches) copies them into
   `UTM_Source` / `UTM_Medium` / `UTM_Campaign` / `UTM_Content` on the member's
   Lead, Contact, Account and Deal. The first value saved is kept; later webhooks
   do not overwrite it. It also fills an empty `Lead_Source` (existing value such
   as Meta Ads / SalesIQ, otherwise `IGP`) and never replaces one.

Leads from Meta lead ads and SalesIQ get their UTM values from those integrations,
not from this flow.

## Not covered here

- The Meta pixels (Directory and Tourist) are not in the footer code. If they are
  installed, they are in BD's header code, which is not in this repo yet.
