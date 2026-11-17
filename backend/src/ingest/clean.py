from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from bs4 import BeautifulSoup
from pypdf import PdfReader

NAV_DATE_FORMATS = ("%d-%b-%Y", "%d %b %Y", "%Y-%m-%d")


def normalize_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _parse_nav_date(raw: str) -> Optional[str]:
    value = raw.strip().replace("'", "")
    # Groww sometimes uses "16 Nov '26"
    m = re.match(r"^(\d{1,2})\s+([A-Za-z]{3})\s+'?(\d{2,4})$", value)
    if m:
        day, mon, year = m.groups()
        if len(year) == 2:
            year = str(2000 + int(year))
        value = f"{int(day):02d}-{mon}-{year}"
    for fmt in NAV_DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _lock_in_text(lock_in: Any) -> str:
    if not isinstance(lock_in, dict):
        return "None"
    years = lock_in.get("years")
    months = lock_in.get("months")
    days = lock_in.get("days")
    parts = []
    if years:
        parts.append(f"{years} year(s)")
    if months:
        parts.append(f"{months} month(s)")
    if days:
        parts.append(f"{days} day(s)")
    return ", ".join(parts) if parts else "None"


def _scheme_facts_from_data(data: dict[str, Any]) -> str:
    lines: list[str] = []

    def add(section: str, body: str) -> None:
        body = (body or "").strip()
        if not body:
            return
        lines.append(section)
        lines.append(body)
        lines.append("")

    scheme_name = str(data.get("scheme_name") or data.get("fund_name") or "").strip()
    if scheme_name:
        add("Scheme", scheme_name)

    fund_house = str(data.get("fund_house") or "").strip()
    if fund_house:
        add("Fund House", fund_house)

    category_bits = [
        str(data.get("category") or "").strip(),
        str(data.get("sub_category") or "").strip(),
        str(data.get("plan_type") or "").strip(),
    ]
    category_bits = [b for b in category_bits if b]
    if category_bits:
        add("Category", " / ".join(category_bits))

    description = str(data.get("description") or "").strip()
    if description:
        add("Investment Objective", description)

    expense = data.get("expense_ratio")
    base_expense = data.get("base_expense_ratio")
    expense_parts = []
    if expense is not None and str(expense).strip():
        expense_parts.append(f"Expense ratio is {expense}%.")
    if base_expense is not None and str(base_expense).strip():
        expense_parts.append(f"Base expense ratio is {base_expense}%.")
    if expense_parts:
        add("Expense Ratio", " ".join(expense_parts))

    exit_load = str(data.get("exit_load") or "").strip()
    if exit_load:
        add("Exit Load", exit_load)

    min_sip = data.get("min_sip_investment")
    if min_sip is not None:
        add("Minimum SIP", f"Minimum SIP amount is Rs {min_sip}.")

    min_lumpsum = data.get("min_investment_amount")
    if min_lumpsum is not None:
        add("Minimum Lumpsum", f"Minimum lumpsum amount is Rs {min_lumpsum}.")

    benchmark = str(data.get("benchmark") or data.get("benchmark_name") or "").strip()
    if benchmark:
        add("Benchmark", f"Benchmark is {benchmark}.")

    risk = str(data.get("nfo_risk") or "").strip()
    if risk:
        add("Riskometer", risk)

    if "lock_in" in data:
        add("Lock-in", f"Lock-in period is {_lock_in_text(data.get('lock_in'))}.")

    stamp = str(data.get("stamp_duty") or "").strip()
    if stamp:
        add("Stamp Duty", f"Stamp duty is {stamp}.")

    nav = data.get("nav")
    nav_date = data.get("nav_date")
    if nav is not None and nav_date:
        add("NAV", f"NAV is {nav} as of {nav_date}.")

    return normalize_text("\n".join(lines))


def _load_mf_server_side_data(soup: BeautifulSoup) -> Optional[dict[str, Any]]:
    node = soup.find("script", id="__NEXT_DATA__")
    if not node or not node.string:
        return None
    try:
        payload = json.loads(node.string)
    except json.JSONDecodeError:
        return None
    data = (
        payload.get("props", {})
        .get("pageProps", {})
        .get("mfServerSideData")
    )
    return data if isinstance(data, dict) else None


def extract_as_of_date(path: Path) -> Optional[str]:
    if path.suffix.lower() not in {".html", ".htm"}:
        return None
    soup = BeautifulSoup(
        path.read_text(encoding="utf-8", errors="ignore"), "html.parser"
    )
    data = _load_mf_server_side_data(soup)
    if not data:
        return None
    nav_date = data.get("nav_date")
    if not nav_date:
        return None
    return _parse_nav_date(str(nav_date))


def _extract_html_fallback(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript", "nav", "header", "footer"]):
        tag.decompose()
    return normalize_text(soup.get_text("\n"))


def extract_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        parts = [page.extract_text() or "" for page in reader.pages]
        return normalize_text("\n".join(parts))
    if path.suffix.lower() in {".html", ".htm"}:
        soup = BeautifulSoup(
            path.read_text(encoding="utf-8", errors="ignore"), "html.parser"
        )
        data = _load_mf_server_side_data(soup)
        if data:
            return _scheme_facts_from_data(data)
        return _extract_html_fallback(soup)
    return normalize_text(path.read_text(encoding="utf-8", errors="ignore"))
