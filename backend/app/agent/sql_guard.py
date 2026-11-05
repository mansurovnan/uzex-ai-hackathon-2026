import re

FORBIDDEN_KEYWORDS = [
    r"\bINSERT\b", r"\bUPDATE\b", r"\bDELETE\b", r"\bDROP\b",
    r"\bALTER\b", r"\bTRUNCATE\b", r"\bCREATE\b", r"\bATTACH\b",
    r"\bDETACH\b", r"\bCOPY\b", r"\bPRAGMA\b", r"\bEXEC\b",
    r"\bSYSTEM\b", r"\bWRITE\b", r"\bEXPORT\b", r"\bIMPORT\b",
    r"\bCALL\b", r"\bLOAD\b", r"\bINSTALL\b"
]

def validate_and_guard_sql(sql: str, default_limit: int = 50) -> str:
    """
    Validates that a SQL query is strictly a read-only SELECT query.
    Raises ValueError if forbidden keywords or syntax are detected.
    Appends LIMIT if none exists on non-aggregate queries.
    """
    cleaned = sql.strip().rstrip(";")
    upper = cleaned.upper()
    
    # Must start with SELECT or WITH
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        raise ValueError("Security Violation: Only SELECT or WITH queries are permitted.")
        
    for pattern in FORBIDDEN_KEYWORDS:
        if re.search(pattern, upper):
            raise ValueError(f"Security Violation: Forbidden keyword detected: {pattern}")
            
    # If no LIMIT and not a single-row aggregate, append limit
    if "LIMIT" not in upper:
        cleaned += f" LIMIT {default_limit}"
        
    return cleaned
