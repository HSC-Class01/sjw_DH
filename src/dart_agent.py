from __future__ import annotations
import io, os, re, zipfile, json, time, logging, calendar
from pathlib import Path
from typing import Any
import requests
import pandas as pd
import yaml
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CONFIG = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
DATA_DIR.mkdir(exist_ok=True)
RAW_DIR.mkdir(exist_ok=True)
OUT = DATA_DIR / "financials.csv"
META = DATA_DIR / "metadata.json"
BASE = "https://opendart.fss.or.kr/api"
REPORT_NAMES = {"11011":"annual", "11012":"half", "11013":"q1", "11014":"q3"}
REPORT_LABELS = {"annual":"Annual", "half":"Half-year", "q1":"Quarterly Q1", "q3":"Quarterly Q3"}

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def api_key() -> str:
    key = os.environ.get("DART_API_KEY", "").strip()
    if not key:
        raise RuntimeError("DART_API_KEY environment variable is required. Add it to GitHub Actions Secrets.")
    return key


def get_json(endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
    p = dict(params); p["crtfc_key"] = api_key()
    r = requests.get(f"{BASE}/{endpoint}.json", params=p, timeout=60)
    r.raise_for_status()
    data = r.json()
    if str(data.get("status")) not in ("000", "013"):
        raise RuntimeError(f"OpenDART {endpoint}: {data.get('status')} {data.get('message')}")
    return data


def num(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    s = str(x).replace(",", "").replace(" ", "").strip()
    if s in ("", "-", "–", "-0"):
        return None
    s = s.replace("△", "-")
    try:
        return float(s)
    except ValueError:
        return None


def account_lookup():
    return CONFIG["metrics"]["accounts"]


def canonical_account(name: str) -> str | None:
    n = re.sub(r"\s+", "", str(name)).lower()
    for key, aliases in account_lookup().items():
        for alias in aliases:
            a = re.sub(r"\s+", "", str(alias)).lower()
            if n == a or a in n or n in a:
                return key
    return None


def fetch_structured(year: int, code: str) -> list[dict[str, Any]]:
    data = get_json("fnlttSinglAcntAll", {
        "corp_code": CONFIG["company"]["corp_code"],
        "bsns_year": str(year),
        "reprt_code": code,
        "fs_div": CONFIG["company"].get("fs_div", "CFS"),
    })
    return data.get("list", [])


def parse_structured(year: int, code: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    period = REPORT_NAMES[code]
    out = {}
    for r in rows:
        key = canonical_account(r.get("account_nm", ""))
        if not key:
            continue
        amount = r.get("thstrm_amount")
        cumulative = r.get("thstrm_add_amount")
        value = num(amount)
        if period in ("half", "q1", "q3") and key in {"revenue","operating_profit","net_income","operating_cash_flow","investing_cash_flow","financing_cash_flow"}:
            # Keep both point-quarter and YTD. The dashboard uses the period's natural value:
            # half = cumulative, Q1/Q3 = 3-month and cumulative fields are retained separately.
            value = num(cumulative) if period == "half" else num(amount)
        if value is not None:
            out[key] = value
        if cumulative is not None:
            out[key + "_ytd"] = num(cumulative)
        if r.get("sj_div") in ("BS",) and key in out:
            out[key] = value
    base = {
        "year": year, "report_code": code, "period": period,
        "report_label": REPORT_LABELS[code], "source": "OpenDART structured API",
        "receipt_no": rows[0].get("rcept_no") if rows else ""
    }
    base.update(out)
    return [base]


def find_filings(year: int, code: str) -> list[dict[str, Any]]:
    # Search the entire year in manageable date windows. This path supports the historical fallback.
    hits = []
    # Annual reports are normally filed in the following calendar year.
    filing_year = year + 1 if code == "11011" else year
    for month in range(1, 13):
        start = f"{filing_year}{month:02d}01"
        last_day = calendar.monthrange(filing_year, month)[1]
        end = f"{filing_year}{month:02d}{last_day:02d}"
        data = get_json("list", {"corp_code": CONFIG["company"]["corp_code"], "bgn_de": start, "end_de": end, "page_no": 1, "page_count": 100})
        for row in data.get("list", []):
            nm = row.get("report_nm", "")
            if code == "11011" and "사업보고서" in nm and "반기" not in nm and "분기" not in nm:
                hits.append(row)
            elif code == "11012" and "반기보고서" in nm:
                hits.append(row)
            elif code == "11013" and "1분기보고서" in nm:
                hits.append(row)
            elif code == "11014" and "3분기보고서" in nm:
                hits.append(row)
        time.sleep(0.08)
    # Prefer the latest final filing if corrections exist.
    hits.sort(key=lambda x: (x.get("rcept_dt", ""), x.get("last_reprt_at", "")), reverse=True)
    return hits[:1]


def parse_legacy_document(year: int, code: str, filing: dict[str, Any]) -> list[dict[str, Any]]:
    rcept = filing["rcept_no"]
    params = {"rcept_no": rcept, "crtfc_key": api_key()}
    r = requests.get(f"{BASE}/document.xml", params=params, timeout=90)
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    extracted = []
    for name in z.namelist():
        if name.lower().endswith((".xml", ".html", ".htm")):
            raw = z.read(name)
            text = raw.decode("utf-8", errors="ignore")
            soup = BeautifulSoup(text, "lxml-xml" if name.lower().endswith(".xml") else "lxml")
            for table in soup.find_all("table"):
                cells = [c.get_text(" ", strip=True) for c in table.find_all(["td","th"])]
                if not cells:
                    continue
                for i, cell in enumerate(cells):
                    key = canonical_account(cell)
                    if key:
                        for nxt in cells[i+1:i+6]:
                            v = num(nxt)
                            if v is not None:
                                extracted.append((key, v)); break
    values = {}
    for key, value in extracted:
        values.setdefault(key, value)
    return [{"year":year,"report_code":code,"period":REPORT_NAMES[code],"report_label":REPORT_LABELS[code],
             "source":"OpenDART original filing XML/HTML fallback","receipt_no":rcept, **values}]


def collect_year(year: int, code: str) -> list[dict[str, Any]]:
    if year >= 2015:
        try:
            rows = fetch_structured(year, code)
            if rows:
                return parse_structured(year, code, rows)
            logging.info("No structured data: %s %s", year, code)
        except Exception as e:
            logging.warning("Structured API failed for %s %s: %s", year, code, e)
    filings = find_filings(year, code)
    if not filings:
        return []
    return parse_legacy_document(year, code, filings[0])


def add_ratios(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Only calculate within the same company and period. Values are in KRW million in OpenDART responses.
    for col in ["revenue","operating_profit","net_income","assets","liabilities","equity","current_assets","current_liabilities","cash","operating_cash_flow","investing_cash_flow","financing_cash_flow","capex"]:
        if col not in df: df[col] = pd.NA
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["revenue_growth"] = df.groupby("period")["revenue"].pct_change() * 100
    df["operating_margin"] = df["operating_profit"] / df["revenue"] * 100
    df["net_margin"] = df["net_income"] / df["revenue"] * 100
    df["roe"] = df["net_income"] / df["equity"] * 100
    df["roa"] = df["net_income"] / df["assets"] * 100
    df["debt_ratio"] = df["liabilities"] / df["equity"] * 100
    df["equity_ratio"] = df["equity"] / df["assets"] * 100
    df["current_ratio"] = df["current_assets"] / df["current_liabilities"] * 100
    df["cfo_margin"] = df["operating_cash_flow"] / df["revenue"] * 100
    if df["capex"].notna().any():
        df["fcf"] = df["operating_cash_flow"] - df["capex"].abs()
    else:
        df["fcf"] = df["operating_cash_flow"] + df["investing_cash_flow"]
    df["fcf_margin"] = df["fcf"] / df["revenue"] * 100
    return df


def main():
    rows = []
    for year in range(int(CONFIG["company"]["start_year"]), pd.Timestamp.today().year + 1):
        for code in CONFIG["company"]["report_codes"].values():
            try:
                got = collect_year(year, code)
                rows.extend(got)
                logging.info("%s %s -> %d rows", year, code, len(got))
            except Exception as e:
                logging.error("%s %s failed: %s", year, code, e)
    if not rows:
        raise RuntimeError("No DART data collected. Check DART_API_KEY and the API response.")
    df = pd.DataFrame(rows).drop_duplicates(subset=["year","report_code","period"], keep="last")
    df = add_ratios(df).sort_values(["period","year","report_code"])
    df.to_csv(OUT, index=False, encoding="utf-8-sig")
    META.write_text(json.dumps({"updated_at":pd.Timestamp.utcnow().isoformat(),"rows":len(df),"company":CONFIG["company"]}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(df)} rows to {OUT}")

if __name__ == "__main__":
    main()
