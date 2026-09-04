#!/usr/bin/env python3
"""Safe Apple -> Google Contacts Phase 2 planner/applicator.

Real contact payloads, OAuth material, plans and receipts are private-local only.
No delete endpoint is implemented. Existing Google contacts are freshly read and
only additively enriched; conflicts and name-only matches are held for review.
"""
from __future__ import annotations

import argparse, base64, hashlib, json, quopri, re, unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE = "https://people.googleapis.com/v1"
FIELDS = "addresses,birthdays,emailAddresses,events,metadata,names,nicknames,organizations,phoneNumbers,photos,urls,userDefined"
VCARD_RE = re.compile(r"BEGIN:VCARD\r?\n(?P<body>.*?)\r?\nEND:VCARD", re.I | re.S)
APPLE_LABEL_RE = re.compile(r"^_\$!<(?P<label>.+)>!\$_$")

@dataclass
class AppleContact:
    ordinal: int
    fingerprint: str
    display_name: str | None = None
    name: dict[str, str] | None = None
    emails: list[dict[str, str]] = field(default_factory=list)
    phones: list[dict[str, str]] = field(default_factory=list)
    addresses: list[dict[str, str]] = field(default_factory=list)
    birthday: dict[str, int] | None = None
    organizations: list[dict[str, Any]] = field(default_factory=list)
    urls: list[dict[str, str]] = field(default_factory=list)
    social_user_defined: list[dict[str, str]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    nicknames: list[dict[str, str]] = field(default_factory=list)
    note: str | None = None
    photo_bytes: bytes | None = None

    def has_meaningful_contact_data(self) -> bool:
        return any((self.display_name, self.emails, self.phones, self.addresses,
                    self.birthday, self.organizations, self.urls,
                    self.social_user_defined, self.events, self.nicknames,
                    self.note, self.photo_bytes))


def normalize_name(value: str | None) -> str | None:
    if not value: return None
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).casefold().strip()) or None


def normalize_email(value: str) -> str | None:
    value = unicodedata.normalize("NFKC", value).strip().casefold()
    if "@" not in value: return None
    local, domain = value.rsplit("@", 1)
    if not local or not domain: return None
    try: domain = domain.encode("idna").decode("ascii")
    except UnicodeError: return None
    return f"{local}@{domain}"


def normalize_phone(value: str, default_region: str = "CA") -> tuple[str | None, bool]:
    raw = unicodedata.normalize("NFKC", value).strip()
    if raw.startswith("00"): raw = "+" + raw[2:]
    cleaned = re.sub(r"[^0-9+]", "", raw)
    if cleaned.count("+") > 1 or ("+" in cleaned and not cleaned.startswith("+")): return None, False
    digits = cleaned[1:] if cleaned.startswith("+") else cleaned
    if not digits.isdigit(): return None, False
    if cleaned.startswith("+"): return cleaned, 8 <= len(digits) <= 15
    if default_region.upper() in {"CA", "US"} and len(digits) == 10: return "+1" + digits, True
    if default_region.upper() in {"CA", "US"} and len(digits) == 11 and digits.startswith("1"): return "+" + digits, True
    return digits or None, False


def _unfold(text: str) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        if line.startswith((" ", "\t")) and out: out[-1] += line[1:]
        else: out.append(line)
    return out


def _decode(raw: str, params: str = "") -> str:
    if "ENCODING=QUOTED-PRINTABLE" in params.upper():
        data = quopri.decodestring(raw)
        try: raw = data.decode("utf-8")
        except UnicodeDecodeError: raw = data.decode("latin-1", errors="replace")
    return raw.replace(r"\n", "\n").replace(r"\N", "\n").replace(r"\,", ",").replace(r"\;", ";").replace(r"\\", "\\").strip()


def _split(raw: str) -> list[str]:
    out, buf, esc = [], [], False
    for ch in raw:
        if esc: buf.extend(["\\", ch]); esc = False
        elif ch == "\\": esc = True
        elif ch == ";": out.append("".join(buf)); buf = []
        else: buf.append(ch)
    if esc: buf.append("\\")
    out.append("".join(buf)); return out


def _head(head: str) -> tuple[str | None, str, dict[str, list[str]]]:
    first, *rest = head.split(";")
    group, key = first.rsplit(".", 1) if "." in first else (None, first)
    params: dict[str, list[str]] = {}
    for part in rest:
        if not part: continue
        if "=" in part:
            k, v = part.split("=", 1); values = [x.strip('"') for x in v.split(",") if x]
            params.setdefault(k.upper(), []).extend(values)
        else: params.setdefault("TYPE", []).append(part)
    return group, key.upper(), params


def _label(value: str | None) -> str | None:
    if not value: return None
    value = _decode(value); match = APPLE_LABEL_RE.match(value)
    return (match.group("label") if match else value).strip() or None


def _type(params: dict[str, list[str]], label: str | None) -> str | None:
    if label:
        low = (_label(label) or "").casefold(); return {"iphone":"mobile","mobile":"mobile","home":"home","work":"work","main":"main","other":"other"}.get(low, _label(label))
    for raw in params.get("TYPE", []):
        low = raw.casefold()
        if low in {"internet","voice","pref"}: continue
        if low in {"cell","iphone"}: return "mobile"
        return low if low in {"home","work","main","other"} else raw
    return None


def _date(raw: str, params: dict[str, list[str]]) -> dict[str, int] | None:
    value = raw.strip().replace("--", "").replace("-", "")
    if not value.isdigit() or len(value) not in {4, 8}: return None
    year = int(value[:4]) if len(value) == 8 else None
    month, day = (int(value[4:6]), int(value[6:8])) if year is not None else (int(value[:2]), int(value[2:4]))
    if year == 1604 and "1604" in params.get("X-APPLE-OMIT-YEAR", []): year = None
    if not (1 <= month <= 12 and 1 <= day <= 31): return None
    result = {"month": month, "day": day}
    if year is not None: result["year"] = year
    return result


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _dedupe(items: list[dict[str, Any]], key) -> list[dict[str, Any]]:
    out, seen = [], set()
    for item in items:
        marker = str(key(item))
        if marker and marker not in seen: seen.add(marker); out.append(item)
    return out


def parse_apple_vcard(path: Path) -> list[AppleContact]:
    text = path.read_text("utf-8", errors="replace"); matches = list(VCARD_RE.finditer(text))
    if not matches: raise ValueError("No vCard records found")
    contacts: list[AppleContact] = []
    for ordinal, match in enumerate(matches, 1):
        block, lines = match.group(0), _unfold(match.group("body")); labels: dict[str, str] = {}
        for line in lines:
            if ":" not in line: continue
            head, raw = line.split(":", 1); group, key, _ = _head(head)
            if group and key == "X-ABLABEL": labels[group] = _decode(raw, ";".join(head.split(";")[1:]))
        c = AppleContact(ordinal, hashlib.sha256(block.encode("utf-8", errors="replace")).hexdigest())
        fn = n_rendered = pending_title = None
        for line in lines:
            if ":" not in line: continue
            head, raw = line.split(":", 1); group, key, params = _head(head); ptxt = ";".join(head.split(";")[1:]); lab = labels.get(group or "")
            if key == "FN": fn = _decode(raw, ptxt) or None
            elif key == "N":
                parts = [_decode(x) for x in _split(raw)] + [""] * 5; family,given,middle,prefix,suffix = parts[:5]
                c.name = {k:v for k,v in {"familyName":family,"givenName":given,"middleName":middle,"honorificPrefix":prefix,"honorificSuffix":suffix}.items() if v} or None
                n_rendered = " ".join(x for x in (prefix,given,middle,family,suffix) if x) or None
            elif key in {"EMAIL","TEL","URL"}:
                value = _decode(raw, ptxt)
                if value:
                    item = {"value": value}; typ = _type(params, lab)
                    if typ: item["type"] = typ
                    {"EMAIL":c.emails,"TEL":c.phones,"URL":c.urls}[key].append(item)
            elif key == "ADR":
                parts = [_decode(x) for x in _split(raw)] + [""] * 7; po,ext,street,city,region,postal,country = parts[:7]
                item = {k:v for k,v in {"poBox":po,"extendedAddress":ext,"streetAddress":street,"city":city,"region":region,"postalCode":postal,"country":country}.items() if v}; typ = _type(params, lab)
                if typ: item["type"] = typ
                if item: c.addresses.append(item)
            elif key == "BDAY" and c.birthday is None: c.birthday = _date(raw, params)
            elif key == "ORG":
                parts = [_decode(x) for x in _split(raw)]; org = {}
                if parts and parts[0]: org["name"] = parts[0]
                if len(parts)>1 and parts[1]: org["department"] = parts[1]
                if pending_title: org["title"] = pending_title; pending_title = None
                if org: c.organizations.append(org)
            elif key == "TITLE":
                title = _decode(raw, ptxt)
                if c.organizations: c.organizations[-1].setdefault("title", title)
                elif title: pending_title = title
            elif key == "X-SOCIALPROFILE":
                value = _decode(raw, ptxt)
                if value.lower().startswith(("http://","https://")): c.urls.append({"value":value,"type":"social"})
                elif value:
                    service = next(iter(params.get("TYPE", [])), None) or "Apple social profile"; userid = next(iter(params.get("X-USERID", [])), None)
                    c.social_user_defined.append({"key":f"Social: {service}","value":userid or value})
            elif key == "X-ABDATE":
                value = _date(raw, params)
                if value: c.events.append({"date":value,"type":_label(lab) or "other"})
            elif key == "NICKNAME":
                value = _decode(raw, ptxt)
                if value: c.nicknames.append({"value":value,"type":"DEFAULT"})
            elif key == "NOTE": c.note = _decode(raw, ptxt) or None
            elif key == "PHOTO" and {x.casefold() for x in params.get("ENCODING", [])} & {"b","base64"}:
                try: photo = base64.b64decode(raw, validate=False)
                except Exception: photo = b""
                if photo.startswith((b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n")): c.photo_bytes = photo
        if pending_title: c.organizations.append({"title":pending_title})
        c.display_name = fn or n_rendered
        if c.name is None and c.display_name: c.name = {"unstructuredName":c.display_name}
        c.emails = _dedupe(c.emails, lambda x: normalize_email(x.get("value","")) or x.get("value",""))
        c.phones = _dedupe(c.phones, lambda x: normalize_phone(x.get("value",""))[0] or x.get("value",""))
        c.addresses = _dedupe(c.addresses, _canon); c.urls = _dedupe(c.urls, lambda x:x.get("value","").casefold())
        c.events = _dedupe(c.events, _canon); c.nicknames = _dedupe(c.nicknames, lambda x:x.get("value","").casefold()); c.social_user_defined = _dedupe(c.social_user_defined, _canon)
        contacts.append(c)
    return contacts


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20), b""): h.update(chunk)
    return h.hexdigest()


def _signals(name: str | None, emails: list[Any], phones: list[Any], nested: bool=False):
    e = {v for item in emails if (v:=normalize_email(item.get("value","") if nested else item))}; p=set()
    for item in phones:
        v,strong=normalize_phone(item.get("value","") if nested else item)
        if v and strong: p.add(v)
    return e,p,normalize_name(name)


def _band(a: AppleContact, g: dict[str, Any]) -> str | None:
    ae,ap,an=_signals(a.display_name,a.emails,a.phones,True); ge,gp,gn=_signals(g.get("display_name"),g.get("emails") or [],g.get("phones") or [])
    se,sp=bool(ae&ge),bool(ap&gp); strong=int(se)+int(sp); same=bool(an and gn and an==gn); conflict=bool(an and gn and an!=gn)
    if strong and conflict: return "conflict"
    if strong>=2 or (strong and same): return "high"
    if strong: return "conflict"
    if same: return "weak"
    return None


def build_plan(vcard_path: Path, google_snapshot_path: Path) -> dict[str, Any]:
    apple=parse_apple_vcard(vcard_path); payload=json.loads(google_snapshot_path.read_text("utf-8")); google=payload.get("contacts") if isinstance(payload,dict) else payload
    if not isinstance(google,list) or any(not isinstance(g.get("external_id"),str) or not g["external_id"].startswith("people/") for g in google): raise ValueError("Google snapshot must contain provider-stable people/... IDs")
    high_a:dict[int,list[str]]={}; high_g:dict[str,list[int]]={}; conflict:set[int]=set(); weak:set[int]=set(); byid={g["external_id"]:g for g in google}
    for a in apple:
        for g in google:
            band=_band(a,g)
            if band=="high": high_a.setdefault(a.ordinal,[]).append(g["external_id"]); high_g.setdefault(g["external_id"],[]).append(a.ordinal)
            elif band=="conflict": conflict.add(a.ordinal)
            elif band=="weak": weak.add(a.ordinal)
    if any(len(v)!=1 for v in high_a.values()) or any(len(v)!=1 for v in high_g.values()): raise ValueError("High-confidence graph is not one-to-one")
    ops=[]; potentials:dict[str,int]={}
    for a in apple:
        base={"apple_ordinal":a.ordinal,"apple_fingerprint":a.fingerprint}
        if a.ordinal in high_a:
            rid=high_a[a.ordinal][0]; g=byid[rid]; fields=[]; ae,ap,_=_signals(a.display_name,a.emails,a.phones,True); ge,gp,_=_signals(g.get("display_name"),g.get("emails") or [],g.get("phones") or [])
            if ae-ge: fields.append("emailAddresses")
            if ap-gp: fields.append("phoneNumbers")
            presence=g.get("field_presence") or {}
            for val,key,target in [(a.addresses,"address","addresses"),(a.birthday,"birthday","birthdays"),(a.organizations,"organization","organizations"),(a.urls or a.social_user_defined,"urls","urls"),(a.events,"events","events")]:
                if val and not presence.get(key): fields.append(target)
            if a.nicknames: fields.append("nicknames")
            if a.photo_bytes: fields.append("photo")
            if a.note: fields.append("note_held")
            fields=sorted(set(fields)); [potentials.__setitem__(f,potentials.get(f,0)+1) for f in fields]
            ops.append({**base,"action":"update","google_external_id":rid,"potential_fields":fields})
        elif a.ordinal in conflict: ops.append({**base,"action":"hold","reason":"identity_conflict"})
        elif a.ordinal in weak: ops.append({**base,"action":"hold","reason":"name_only_weak_match"})
        elif a.has_meaningful_contact_data(): ops.append({**base,"action":"create"})
        else: ops.append({**base,"action":"hold","reason":"empty_contact"})
    stats={"apple_contacts":len(apple),"google_contacts":len(google),"updates":sum(x["action"]=="update" for x in ops),"creates":sum(x["action"]=="create" for x in ops),"holds_conflict":sum(x.get("reason")=="identity_conflict" for x in ops),"holds_weak":sum(x.get("reason")=="name_only_weak_match" for x in ops),"holds_empty":sum(x.get("reason")=="empty_contact" for x in ops),"apple_notes_held":sum(bool(x.note) for x in apple),"apple_photos":sum(bool(x.photo_bytes) for x in apple),"potential_fields":dict(sorted(potentials.items()))}
    return {"schema_version":1,"generated_at":datetime.now(timezone.utc).isoformat(),"safety":{"provider_deletion_implemented":False,"existing_names_overwritten":False,"notes_auto_written":False,"conflict_or_weak_matches_written":False,"updates_are_additive_after_fresh_get":True},"sources":{"apple_vcard_sha256":_sha(vcard_path),"google_snapshot_sha256":_sha(google_snapshot_path)},"stats":stats,"operations":ops}


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+".tmp"); tmp.write_text(json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False)+"\n","utf-8"); tmp.replace(path)

_ALLOWED={
"emailAddresses":{"value","type"},"phoneNumbers":{"value","type"},"addresses":{"formattedValue","type","poBox","streetAddress","extendedAddress","city","region","postalCode","country","countryCode"},"birthdays":{"date","text"},"events":{"date","type"},"nicknames":{"value","type"},"organizations":{"type","startDate","endDate","current","name","phoneticName","department","title","jobDescription","symbol","domain","location","costCenter","fullTimeEquivalentMillipercent"},"urls":{"value","type"},"userDefined":{"key","value"}}

def _clean(field: str, item: dict[str,Any]) -> dict[str,Any]: return {k:v for k,v in item.items() if k in _ALLOWED[field] and v not in (None,"",[],{})}
def _sig(field: str, item: dict[str,Any]) -> str:
    if field=="emailAddresses": return normalize_email(item.get("value","")) or item.get("value","").casefold()
    if field=="phoneNumbers": return normalize_phone(item.get("value",""))[0] or item.get("value","")
    if field in {"urls","nicknames"}: return item.get("value","").strip().casefold()
    return _canon(_clean(field,item))
def _union(field: str, existing:list[dict[str,Any]], incoming:list[dict[str,Any]]):
    out=[_clean(field,x) for x in existing]; seen={_sig(field,x) for x in out}; changed=False
    for raw in incoming:
        item=_clean(field,raw); marker=_sig(field,item)
        if marker and marker not in seen: seen.add(marker); out.append(item); changed=True
    return out,changed

def _same_date(a:dict[str,Any],b:dict[str,Any]): return {k:a.get(k) for k in ("year","month","day") if a.get(k) is not None}=={k:b.get(k) for k in ("year","month","day") if b.get(k) is not None}


def build_update_payload(current: dict[str,Any], apple: AppleContact):
    body={"metadata":{"sources":[s for s in (current.get("metadata") or {}).get("sources",[]) if s.get("type")=="CONTACT"]}}; fields=[]; holds=[]
    for field_name,values in {"emailAddresses":apple.emails,"phoneNumbers":apple.phones,"urls":apple.urls,"events":apple.events,"nicknames":apple.nicknames,"userDefined":apple.social_user_defined}.items():
        if values:
            merged,changed=_union(field_name,current.get(field_name) or [],values)
            if changed: body[field_name]=merged; fields.append(field_name)
    if apple.addresses:
        existing=current.get("addresses") or []
        if not existing: body["addresses"]=[_clean("addresses",x) for x in apple.addresses]; fields.append("addresses")
        elif any(_sig("addresses",x) not in {_sig("addresses",e) for e in existing} for x in apple.addresses): holds.append("address_requires_review")
    if apple.organizations:
        orgs=[_clean("organizations",x) for x in (current.get("organizations") or [])]; changed=False; conflict=False
        for inc in apple.organizations:
            inc=_clean("organizations",inc); name=normalize_name(inc.get("name")); idx=next((i for i,x in enumerate(orgs) if name and normalize_name(x.get("name"))==name),None)
            if idx is None:
                if _sig("organizations",inc) not in {_sig("organizations",x) for x in orgs}: orgs.append(inc); changed=True
            else:
                candidate=dict(orgs[idx])
                for attr in ("department","title"):
                    incoming,existing=inc.get(attr),candidate.get(attr)
                    if incoming and not existing: candidate[attr]=incoming; changed=True
                    elif incoming and existing and normalize_name(str(incoming))!=normalize_name(str(existing)): conflict=True
                orgs[idx]=candidate
        if conflict: holds.append("organization_requires_review")
        elif changed: body["organizations"]=orgs; fields.append("organizations")
    if apple.birthday:
        birthdays=current.get("birthdays") or []
        if not birthdays: body["birthdays"]=[{"date":apple.birthday}]; fields.append("birthdays")
        elif not any(_same_date(x.get("date") or {},apple.birthday) for x in birthdays): holds.append("birthday_conflict")
    if apple.note: holds.append("note_requires_classification")
    contact_photos=[p for p in (current.get("photos") or []) if ((p.get("metadata") or {}).get("source") or {}).get("type")=="CONTACT"]
    photo_safe=bool(apple.photo_bytes) and (not contact_photos or all(bool(p.get("default")) for p in contact_photos))
    return body,sorted(set(fields)),sorted(set(holds)),photo_safe


def build_create_payload(apple: AppleContact):
    body={}
    if apple.name: body["names"]=[apple.name]
    for k,v in {"emailAddresses":apple.emails,"phoneNumbers":apple.phones,"addresses":apple.addresses,"organizations":apple.organizations,"urls":apple.urls,"events":apple.events,"nicknames":apple.nicknames,"userDefined":apple.social_user_defined}.items():
        if v: body[k]=v
    if apple.birthday: body["birthdays"]=[{"date":apple.birthday}]
    return body,(["note_requires_classification"] if apple.note else [])


def _session(client:Path,token:Path):
    try:
        from google.auth.transport.requests import AuthorizedSession
        from google_people_phase2 import _load_credentials
    except ImportError as exc: raise SystemExit("Install requirements-people-phase2.txt and run from the repo") from exc
    return AuthorizedSession(_load_credentials(client,token))
def _get(session,rid):
    r=session.get(f"{BASE}/{rid}",params={"personFields":FIELDS,"sources":"READ_SOURCE_TYPE_CONTACT"},timeout=60)
    if r.status_code>=400: raise RuntimeError(f"People GET failed ({r.status_code}): {r.text[:500]}")
    return r.json()
def _patch(session,rid,body,fields):
    r=session.patch(f"{BASE}/{rid}:updateContact",params={"updatePersonFields":",".join(fields)},json=body,timeout=60)
    if r.status_code>=400: raise RuntimeError(f"People update failed ({r.status_code}): {r.text[:500]}")
    return r.json()
def _create(session,body):
    r=session.post(f"{BASE}/people:createContact",params={"personFields":FIELDS},json=body,timeout=60)
    if r.status_code>=400: raise RuntimeError(f"People create failed ({r.status_code}): {r.text[:500]}")
    return r.json()
def _photo(session,rid,data):
    r=session.patch(f"{BASE}/{rid}:updateContactPhoto",json={"photoBytes":base64.b64encode(data).decode("ascii")},timeout=60)
    if r.status_code>=400: raise RuntimeError(f"People photo update failed ({r.status_code}): {r.text[:500]}")


def apply_plan(plan_path:Path,vcard:Path,snapshot:Path,receipt_path:Path,*,client_secret:Path,token_path:Path,refreshed_snapshot_path:Path,apply:bool):
    plan=json.loads(plan_path.read_text("utf-8"))
    if plan.get("sources",{}).get("apple_vcard_sha256")!=_sha(vcard) or plan.get("sources",{}).get("google_snapshot_sha256")!=_sha(snapshot): raise ValueError("Source digest changed; regenerate plan")
    apple={x.ordinal:x for x in parse_apple_vcard(vcard)}
    if any(op.get("apple_ordinal") not in apple or apple[op["apple_ordinal"]].fingerprint!=op.get("apple_fingerprint") for op in plan.get("operations") or []): raise ValueError("Plan no longer maps to vCard")
    if not apply: return {"dry_run":True,**plan["stats"]}
    session=_session(client_secret,token_path); receipt=json.loads(receipt_path.read_text("utf-8")) if receipt_path.exists() else {"schema_version":1,"started_at":datetime.now(timezone.utc).isoformat(),"results":{}}; results=receipt.setdefault("results",{}); counts={"updated":0,"created":0,"skipped_receipt":0,"held":0,"field_holds":0,"photos_written":0}
    for op in plan["operations"]:
        fp=op["apple_fingerprint"]
        if results.get(fp,{}).get("status")=="success": counts["skipped_receipt"]+=1; continue
        a=apple[op["apple_ordinal"]]
        if op["action"]=="hold": results[fp]={"status":"held","reason":op.get("reason")}; counts["held"]+=1; write_json_atomic(receipt_path,receipt); continue
        try:
            if op["action"]=="update":
                rid=op["google_external_id"]; current=_get(session,rid); body,fields,holds,photo_safe=build_update_payload(current,a)
                if fields: rid=_patch(session,rid,body,fields).get("resourceName") or rid; counts["updated"]+=1
                if photo_safe and a.photo_bytes: _photo(session,rid,a.photo_bytes); counts["photos_written"]+=1
                counts["field_holds"]+=len(holds); results[fp]={"status":"success","action":"update","google_external_id":rid,"updated_fields":fields,"field_holds":holds,"photo_written":bool(photo_safe and a.photo_bytes)}
            elif op["action"]=="create":
                body,holds=build_create_payload(a)
                if not body: results[fp]={"status":"held","reason":"no_writable_fields"}; counts["held"]+=1
                else:
                    created=_create(session,body); rid=created.get("resourceName")
                    if not isinstance(rid,str) or not rid.startswith("people/"): raise RuntimeError("Create returned no stable people/... ID")
                    if a.photo_bytes: _photo(session,rid,a.photo_bytes); counts["photos_written"]+=1
                    counts["created"]+=1; counts["field_holds"]+=len(holds); results[fp]={"status":"success","action":"create","google_external_id":rid,"field_holds":holds,"photo_written":bool(a.photo_bytes)}
            else: raise ValueError("Unknown action")
        except Exception as exc: results[fp]={"status":"error","action":op["action"],"error":str(exc)[:1000]}; receipt["last_error_at"]=datetime.now(timezone.utc).isoformat(); write_json_atomic(receipt_path,receipt); raise
        receipt["updated_at"]=datetime.now(timezone.utc).isoformat(); write_json_atomic(receipt_path,receipt)
    from google_people_phase2 import enumerate_saved_contacts, write_snapshot
    contacts,sync=enumerate_saved_contacts(client_secret=client_secret,token_path=token_path,account_scope="google-primary"); write_snapshot(contacts,output=refreshed_snapshot_path,account_scope="google-primary",next_sync_token=sync)
    receipt.update({"completed_at":datetime.now(timezone.utc).isoformat(),"aggregate":counts,"refreshed_google_contacts":len(contacts)}); write_json_atomic(receipt_path,receipt)
    return {**counts,"refreshed_google_contacts":len(contacts),"private_receipt":str(receipt_path),"refreshed_snapshot":str(refreshed_snapshot_path)}


def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest="cmd",required=True)
    plan=sub.add_parser("plan"); plan.add_argument("--apple-vcard",type=Path,default=Path(".private/people/apple_contacts.vcf")); plan.add_argument("--google-snapshot",type=Path,default=Path(".private/people/google_people_live.json")); plan.add_argument("--output",type=Path,default=Path(".private/people/apple_google_plan.json"))
    app=sub.add_parser("apply"); app.add_argument("--plan",type=Path,default=Path(".private/people/apple_google_plan.json")); app.add_argument("--apple-vcard",type=Path,default=Path(".private/people/apple_contacts.vcf")); app.add_argument("--google-snapshot",type=Path,default=Path(".private/people/google_people_live.json")); app.add_argument("--receipt",type=Path,default=Path(".private/people/apple_google_apply_receipt.json")); app.add_argument("--client-secret",type=Path,default=Path(".private/people/google-oauth-client.json")); app.add_argument("--token",type=Path,default=Path(".private/people/google-people-token.json")); app.add_argument("--refreshed-snapshot",type=Path,default=Path(".private/people/google_people_live_after_apple.json")); app.add_argument("--apply",action="store_true")
    a=p.parse_args()
    if a.cmd=="plan": value=build_plan(a.apple_vcard,a.google_snapshot); write_json_atomic(a.output,value); print(json.dumps({"private_plan":str(a.output),**value["stats"]},indent=2,sort_keys=True))
    else: print(json.dumps(apply_plan(a.plan,a.apple_vcard,a.google_snapshot,a.receipt,client_secret=a.client_secret,token_path=a.token,refreshed_snapshot_path=a.refreshed_snapshot,apply=a.apply),indent=2,sort_keys=True))

if __name__=="__main__": main()
