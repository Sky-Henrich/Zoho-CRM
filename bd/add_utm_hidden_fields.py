#!/usr/bin/env python3
"""Add the 4 hidden UTM fields to Brilliant Directories forms via the BD API.

Adds utm_source, utm_medium, utm_campaign and utm_content as Hidden fields
(empty default) to each form. The site-wide script bd/utm_capture.html fills
them in the browser; BD then posts them with the lead/member, and the Zoho
functions copy them into UTM_Source / UTM_Medium / UTM_Campaign / UTM_Content.

Safe by default: it first GETs each form's current fields (same call as the
export: /api/v2/form_fields/get?property=form_name&property_value=<form>),
skips any UTM field that already exists, and only PRINTS what it would do.
Pass --apply to actually create the fields.

Usage:
  export BD_API_KEY=...            # never commit the key
  python3 bd/add_utm_hidden_fields.py                 # dry run, 7 Get Matched forms
  python3 bd/add_utm_hidden_fields.py --apply
  python3 bd/add_utm_hidden_fields.py --forms <join_form> <claim_form> --apply

The create call (POST /api/v2/form_fields/create) mirrors the column names of
the GET export; if BD answers with an error, the response is printed and
nothing else is attempted for that form - add the fields by hand in
BD Admin > form editor instead (type Hidden, names as below).
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

SITE = "https://www.igopanama.com"

GET_MATCH_FORMS = [
    "bootstrap_get_match",
    "bootstrap_get_match_community",
    "bootstrap_get_match_experience",
    "bootstrap_get_match_live",
    "bootstrap_get_match_relocate",
    "bootstrap_get_match_stay",
    "bootstrap_get_match_visit",
]

# field_name -> (field_label, field_order). Orders sit right after url_from
# (250 on the custom forms); position is irrelevant for hidden fields.
UTM_FIELDS = {
    "utm_source": ("UTM Source", 251),
    "utm_medium": ("UTM Medium", 252),
    "utm_campaign": ("UTM Campaign", 253),
    "utm_content": ("UTM Content", 254),
}


def call(api_key, method, path, params):
    data = urllib.parse.urlencode(params)
    url = SITE + path
    body = None
    if method == "GET":
        url += "?" + data
    else:
        body = data.encode()
    req = urllib.request.Request(url, data=body, method=method, headers={
        "X-Api-Key": api_key,
        "Content-Type": "application/x-www-form-urlencoded",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def existing_field_names(api_key, form):
    resp = call(api_key, "GET", "/api/v2/form_fields/get",
                {"property": "form_name", "property_value": form})
    if resp.get("status") != "success":
        raise RuntimeError(f"GET failed for {form}: {resp}")
    rows = resp.get("message") or []
    return {r.get("field_name") for r in rows if isinstance(r, dict)}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--forms", nargs="+", default=GET_MATCH_FORMS,
                    help="BD form_name values (default: the 7 Get Matched forms)")
    ap.add_argument("--apply", action="store_true",
                    help="create the fields (default is a dry run)")
    args = ap.parse_args()

    api_key = os.environ.get("BD_API_KEY")
    if not api_key:
        sys.exit("Set BD_API_KEY in the environment first.")

    for form in args.forms:
        try:
            have = existing_field_names(api_key, form)
        except Exception as e:  # noqa: BLE001 - report and continue
            print(f"[{form}] could not read fields: {e}")
            continue
        missing = [f for f in UTM_FIELDS if f not in have]
        if not missing:
            print(f"[{form}] all UTM fields already present")
            continue
        for name in missing:
            label, order = UTM_FIELDS[name]
            params = {
                "form_name": form,
                "field_name": name,
                "field_label": label,
                "field_type": "Hidden",
                "default_value": "",
                "required": "0",
                "field_order": str(order),
            }
            if not args.apply:
                print(f"[{form}] would create hidden field {name}")
                continue
            resp = call(api_key, "POST", "/api/v2/form_fields/create", params)
            if resp.get("status") != "success":
                print(f"[{form}] create {name} FAILED: {resp}")
                break
            print(f"[{form}] created hidden field {name}")
    if not args.apply:
        print("\nDry run only - re-run with --apply to create the fields.")


if __name__ == "__main__":
    main()
