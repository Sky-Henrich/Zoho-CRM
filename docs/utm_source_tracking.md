# UTM source tracking: BD website forms → Zoho CRM

Goal (Sarah): every lead and signup from the website arrives in Zoho carrying
its real source, so Sofia can report reach → traffic → leads → deals by
channel (Instagram bio, TikTok, YouTube…) and by arm (Directory vs English).

## 1. What the fresh form export shows (7 Get Matched forms)

Export via `GET /api/v2/form_fields/get?property=form_name&property_value=<form>`.

| Form | Hidden fields today | Source-type fields today |
|---|---|---|
| `bootstrap_get_match` (default) | none | `url_from` (Textbox, origin URL) |
| `bootstrap_get_match_community` | `top_id` = 3 | `url_from` |
| `bootstrap_get_match_experience` | `top_id` = 14 | `url_from` |
| `bootstrap_get_match_live` | `top_id` = 4 | `url_from` |
| `bootstrap_get_match_relocate` | `top_id` = 15 | `url_from` |
| `bootstrap_get_match_stay` | `top_id` = 16 | `url_from` |
| `bootstrap_get_match_visit` | `top_id` = 10 | `url_from` |

**None of the forms has any UTM field yet.** The only hidden field is `top_id`
(it fixes the category) and the only source-like field is `url_from`. That is
the page the form was sent from. It is not the channel, because the UTM links
land on other pages first.

## 2. Field naming (same on every form, matches the Zoho API names)

| BD form field (`field_name`, type Hidden) | Zoho field (API name) | Example value |
|---|---|---|
| `utm_source` | `UTM_Source` | `instagram` |
| `utm_medium` | `UTM_Medium` | `bio` |
| `utm_campaign` | `UTM_Campaign` | `ind-organic-2026-10` |
| `utm_content` | `UTM_Content` | *(blank for now; free for later A/B links)* |

The arm comes from the campaign prefix: `bus-…` means Directory (Spanish,
businesses) and `ind-…` means English (tourists & expats). Only the date part
changes each month, so a Zoho formula field such as
`If(StartsWith(${Leads.UTM Campaign},'bus-'),'Directory','English')`
gives the arm split without a fifth hidden field.

## 3. The three pieces

1. **Site-wide capture script**: `bd/utm_capture.html`. It is pasted once
   into BD's site-wide footer/custom-code area. The UTM links land on
   `/marketing-results`, `/business`, `/join-individual`, `/guides` and
   `/find-a-business`, not on the forms. The script saves the `utm_` values
   in a 30-day first-party cookie on arrival and fills the hidden fields when
   a form opens or submits. A new UTM link replaces the stored values; plain
   visits keep them. Tested in Chromium: the values survive navigating to
   another page, fill a form that loads late (modal/AJAX), and aren't
   cleared by a later plain visit.
2. **Hidden fields on the forms**: `bd/add_utm_hidden_fields.py` adds the 4
   Hidden fields through the BD API (it does a dry run by default and skips
   fields that already exist). By default it covers the 7 Get Matched forms.
   Run it again with `--forms <name> …` for the **join, claim and
   business-enquiry signup forms**; their `form_name` values aren't in this
   export. Adding the fields by hand in the BD form editor works just as
   well.
3. **Zoho mapping**:
   - *Member signups* (join / claim / business signup):
     `functions/standalone/bd_sync_active_members.dg` reads the 4 values
     from the webhook body or BD's live user API. It then writes them to
     every record the member became: Lead, Contact, Account and Deal,
     matched by `BD_Member_ID`. The first touch wins, so a record that
     already has `UTM_Source` is never overwritten.
   - *Get Matched enquiries*: see "Open item" below.

## 4. Zoho fields needed

`UTM_Source`, `UTM_Medium`, `UTM_Campaign` and `UTM_Content` (Single Line)
exist on **Leads**. The same four API names are also needed on **Contacts**,
**Accounts** and **Deals**:

- **Individual** signups go to Contacts only and never create a Lead, so a
  Leads-only setup loses the whole English arm.
- The "deals by channel" report needs the values on Deals.

Until a module has the fields, the function just logs a warning for that
module. The rest of the sync is unaffected.

## 5. Open item: Get Matched enquiries

The member sync above handles members (signups and plan changes). It does
**not** handle Get Matched enquiries: those are BD *leads*, a different
webhook, and no function in this repo processes them. To finish that path we
need either:
- the Zoho function or integration that already receives them (so the four
  `utm_*` values can be added to its Lead mapping), or
- a sample body from BD's lead webhook, so a new function can be written.
