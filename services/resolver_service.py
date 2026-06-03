"""
Product Resolver Service
The brain of the voice ordering system.

Flow:
1. Extract quantity + unit from query using regex
2. Strip quantity/unit from query to get the clean product name text
3. Search products using ILIKE + pg_trgm fuzzy on name
4. Filter results to only those in the customer's Redis allowed_products set
5. Determine if we have: exact/confident match, clarification_required (multiple families), or not_found
"""

import re
import asyncio
from functools import partial
from typing import Optional
from core.database import get_pool
from core.redis_client import get_customer_allowed_products

# ── Unit Conversion Table ─────────────────────────────────────────────────────
# Maps user-spoken unit variants → (normalized_unit, conversion_factor_to_base)
UNIT_MAP = {
    # Weight
    "kg":     ("kg", 1.0),
    "kgs":    ("kg", 1.0),
    "kilo":   ("kg", 1.0),
    "kilos":  ("kg", 1.0),
    "kilogram":  ("kg", 1.0),
    "kilograms": ("kg", 1.0),
    "g":      ("kg", 0.001),
    "gm":     ("kg", 0.001),
    "gram":   ("kg", 0.001),
    "grams":  ("kg", 0.001),
    "lb":     ("kg", 0.4536),
    "lbs":    ("kg", 0.4536),
    "pound":  ("kg", 0.4536),
    "pounds": ("kg", 0.4536),
    # Volume
    "l":      ("l", 1.0),
    "ltr":    ("l", 1.0),
    "litre":  ("l", 1.0),
    "litres": ("l", 1.0),
    "liter":  ("l", 1.0),
    "liters": ("l", 1.0),
    "ml":     ("l", 0.001),
    "milliliter":  ("l", 0.001),
    "milliliters": ("l", 0.001),
    # Count / Packaging 
    "ctn":    ("ctn", 1.0),
    "carton": ("ctn", 1.0),
    "cartons":("ctn", 1.0),
    "cs":     ("ctn", 1.0),
    "case":   ("ctn", 1.0),
    "cases":  ("ctn", 1.0),
    "pk":     ("pk", 1.0),
    "pack":   ("pk", 1.0),
    "packs":  ("pk", 1.0),
    "btl":    ("btl", 1.0),
    "bottle": ("btl", 1.0),
    "bottles":("btl", 1.0),
    "pun":    ("pun", 1.0),
    "punnet": ("pun", 1.0),
    "punnets":("pun", 1.0),
    "bag":    ("bag", 1.0),
    "bags":   ("bag", 1.0),
    "box":    ("box", 1.0),
    "boxes":  ("box", 1.0),
    "ea":     ("ea", 1.0),
    "each":   ("ea", 1.0),
    "pc":     ("ea", 1.0),
    "piece":  ("ea", 1.0),
    "pieces": ("ea", 1.0),
    "doz":    ("doz", 1.0),
    "dozen":  ("doz", 1.0),
    "dozens": ("doz", 1.0),
}

# Fractional orders not allowed for whole-count units
WHOLE_UNITS = {"ctn", "pk", "btl", "box", "doz"}

# ── Regex: Extract quantity + unit from phrase ────────────────────────────────
QTY_PATTERN = re.compile(
    r"""
    (?P<qty>
        \d+(?:[.,]\d+)?       # e.g. 2, 0.5, 1,000
        |\bhalf\b             # "half"
        |\bquarter\b          # "quarter"
    )
    \s*
    (?P<unit>
        """ + "|".join(sorted(UNIT_MAP.keys(), key=len, reverse=True)) + r"""
    )?
    """,
    re.VERBOSE | re.IGNORECASE,
)

FRACTION_WORDS = {"half": 0.5, "quarter": 0.25}


def extract_quantity_unit(text: str) -> tuple[Optional[float], Optional[str], str]:
    """
    Returns (qty, raw_unit, cleaned_text)
    cleaned_text has the quantity+unit portion removed.
    """
    match = QTY_PATTERN.search(text)
    if not match:
        return None, None, text.strip()

    raw_qty = match.group("qty").lower()
    raw_unit = (match.group("unit") or "").lower().strip()
    
    qty = FRACTION_WORDS.get(raw_qty, None)
    if qty is None:
        try:
            qty = float(raw_qty.replace(",", ""))
        except ValueError:
            qty = None

    # Remove the matched portion from text
    cleaned = (text[:match.start()] + text[match.end():]).strip()
    return qty, raw_unit or None, cleaned


def normalize_unit(raw_unit: str) -> tuple[str, float]:
    """Return (normalized_unit, conversion_factor) from raw user unit."""
    return UNIT_MAP.get(raw_unit.lower(), (raw_unit.lower(), 1.0))


def extract_product_family_from_name(name: str) -> str:
    """
    Heuristic: strip trailing unit-like tokens from a product name to get the family.
    E.g. "APPLES GREEN PER KG" → "APPLES GREEN"
         "PEACHES PER 5KG CTN" → "PEACHES"
    """
    # Remove unit-like tokens and PER/x from end
    stripped = re.sub(
        r"\s+(per\s+)?(\d+\s*)?(kg|g|l|ml|ctn|pk|btl|pun|bag|box|ea|each|doz|dozen|piece|pieces|lb|lbs)\s*$",
        "",
        name,
        flags=re.IGNORECASE,
    ).strip()
    # Also remove "PER" from tail if it remains
    stripped = re.sub(r"\s+PER\s*$", "", stripped, flags=re.IGNORECASE).strip()
    return stripped.upper()


def _difflib_fuzzy_match(product_text: str, candidates: list[dict], cutoff: float = 0.50) -> list[dict]:
    """
    Intelligent fuzzy matching.
    Calculates score based on:
    1. Difflib ratio between query and tokens.
    2. First-letter match bonus (typos rarely change the starting phonetic character).
    3. Prefix matching bonus.
    """
    import difflib
    query_lower = product_text.lower().strip()
    q_len = len(query_lower)
    if q_len == 0:
        return []

    scored = []
    for row in candidates:
        name = row["name"].lower()
        tokens = name.split()
        
        best_token_score = 0.0
        for tok in tokens:
            base_score = difflib.SequenceMatcher(None, query_lower, tok).ratio()
            
            # Massive bonus for first character match, or heavy penalty if mismatch
            if tok and query_lower[0] == tok[0]:
                base_score += 0.20
            else:
                base_score -= 0.30  # Crucial for filtering distinct words
            
            # Bonus if one is a prefix of another
            if tok.startswith(query_lower) or query_lower.startswith(tok):
                base_score += 0.15
                
            # Penalty if lengths are vastly different and it's not a prefix
            if not tok.startswith(query_lower):
                len_diff = abs(len(tok) - q_len)
                if len_diff > 3:
                     base_score -= 0.15

            best_token_score = max(best_token_score, base_score)

        # Full string comparison as backup
        full_score = difflib.SequenceMatcher(None, query_lower, name).ratio()
        if query_lower[0] == name[0]:
            full_score += 0.10
        else:
            full_score -= 0.20
        
        final_score = max(best_token_score, full_score)
        
        if final_score >= cutoff:
            scored.append((final_score, row))
            
    scored.sort(key=lambda x: x[0], reverse=True)
    return [row for _, row in scored]


async def resolve_product(customer_id: int, query: str) -> dict:
    """
    Core resolver function.
    Returns a dict matching ResolveResponse schema.
    """
    pool = get_pool()

    # Step 1: Quantity + Unit extraction
    qty, raw_unit, product_text = extract_quantity_unit(query)

    # Step 2: Get customer's allowed products from Redis
    allowed = await get_customer_allowed_products(customer_id)

    if not product_text:
        product_text = query.strip()

    rows = []

    # ── Layer 1: ILIKE substring match ────────────────────────────────────
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT product_id, name, order_unit, min_order_qty
            FROM products
            WHERE is_active = true
              AND name ILIKE $1
            LIMIT 20
        """, f"%{product_text}%")

    # ── Layer 2: Word-level ILIKE ─────────────────────────────────────────
    if not rows:
        words = [w for w in product_text.split() if len(w) >= 3]
        if words:
            async with pool.acquire() as conn:
                query_conds = " AND ".join(f"name ILIKE ${i+1}" for i in range(len(words)))
                params = [f"%{w}%" for w in words]
                
                rows = await conn.fetch(f"""
                    SELECT product_id, name, order_unit, min_order_qty FROM products
                    WHERE is_active = true AND {query_conds}
                    LIMIT 20
                """, *params)

    # ── Layer 3: Difflib fuzzy (CPU-bound, runs in thread pool) ───────────
    if not rows:
        async with pool.acquire() as conn:
            if allowed:
                all_products = await conn.fetch("""
                    SELECT product_id, name, order_unit, min_order_qty FROM products
                    WHERE is_active = true AND product_id = ANY($1::int[])
                """, list(allowed))
            else:
                all_products = await conn.fetch("""
                    SELECT product_id, name, order_unit, min_order_qty FROM products
                    WHERE is_active = true LIMIT 500
                """)

        if not all_products:
            return {"status": "not_found", "alternatives": []}

        product_dicts = [dict(r) for r in all_products]
        loop = asyncio.get_event_loop()
        rows = await loop.run_in_executor(
            None,
            partial(_difflib_fuzzy_match, product_text, product_dicts, 0.40)
        )
        rows = rows[:20]

        if not rows:
            return {"status": "not_found", "alternatives": []}

    # ── Ensure rows are dicts ─────────────────────────────────────────────
    rows = [dict(r) if not isinstance(r, dict) else r for r in rows]

    # Step 4: Filter to only customer's allowed products
    if allowed:
        filtered = [r for r in rows if r["product_id"] in allowed]
    else:
        filtered = list(rows)

    if not filtered:
        return {
            "status": "not_found",
            "alternatives": [r["name"] for r in rows[:5]]
        }

    # Step 5: Unit filtering
    unit_filtered = filtered
    norm_unit = None
    factor = 1.0
    if raw_unit:
        norm_unit, factor = normalize_unit(raw_unit)
        unit_match = [
            r for r in filtered
            if r["order_unit"] and norm_unit.lower() in r["order_unit"].lower()
        ]
        if unit_match:
            unit_filtered = unit_match

    # Step 6: Group by product family
    family_groups: dict[str, list] = {}
    for r in unit_filtered:
        family = extract_product_family_from_name(r["name"])
        family_groups.setdefault(family, []).append(r)

    # Step 7: Resolution decision
    if len(family_groups) == 1:
        # Only one family matched. Let's see how many variants
        family_key = list(family_groups.keys())[0]
        candidates = family_groups[family_key]
        
        if len(candidates) == 1:
            product = candidates[0]
            norm_qty = None
            if qty is not None and factor:
                norm_qty = round(qty * factor, 4)

            # Whole-unit fraction check
            if norm_unit in WHOLE_UNITS and qty is not None and qty != int(qty):
                return {
                    "status": "matched",
                    "matched": True,
                    "valid": False,
                    "product_id": product["product_id"],
                    "product_name": product["name"],
                    "unit": product["order_unit"],
                    "message": f"'{product['order_unit']}' can only be ordered in whole numbers, not fractions."
                }

            # Step / Min Quantity multiple check
            min_qty = product.get("min_order_qty")
            # Ensure it is a valid float
            try:
                min_qty = float(min_qty) if min_qty is not None else 1.0
            except (ValueError, TypeError):
                min_qty = 1.0
                
            if norm_qty is not None and min_qty > 0:
                # Check if norm_qty is a multiple of min_qty
                # Use round to avoid floating point imprecision
                remainder = round((norm_qty % min_qty), 4)
                if remainder != 0 and remainder != min_qty:
                    # Not a proper multiple
                    return {
                        "status": "matched",
                        "matched": True,
                        "valid": False,
                        "product_id": product["product_id"],
                        "product_name": product["name"],
                        "unit": product["order_unit"],
                        "message": f"This product must be ordered in multiples of {min_qty} {product['order_unit']}. You cannot order {norm_qty}."
                    }

            return {
                "status": "matched",
                "product_id": product["product_id"],
                "product_name": product["name"],
                "quantity": qty,
                "unit": raw_unit or product["order_unit"],
                "normalized_quantity": norm_qty or qty,
                "normalized_unit": norm_unit or product["order_unit"],
                "confidence": 0.95,
            }
        else:
            # Multiple variants in ONE family
            options = [
                {"product_id": r["product_id"], "name": r["name"], "unit": r["order_unit"] or ""}
                for r in candidates[:8]
            ]
            return {
                "status": "clarification_required",
                "product_family": family_key,
                "options": options,
            }
            
    # If MULTIPLE families matched (e.g. fuzzy match gave Kale, Apple, Pineapple)
    # We should return the top option from each family to let the user clarify what they meant.
    options = []
    for family, cands in list(family_groups.items())[:8]:
        r = cands[0] # Pick the best matching variant from this family
        options.append({
            "product_id": r["product_id"], 
            "name": r["name"], 
            "unit": r["order_unit"] or ""
        })

    return {
        "status": "clarification_required",
        "product_family": "MULTIPLE_FAMILIES_MATCHED",
        "options": options,
    }

