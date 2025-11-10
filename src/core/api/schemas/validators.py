def validate_non_empty_str(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Value cannot be empty or only contain whitespace")

    if any(ch in value for ch in ("\n", "\r", "\t")):
        raise ValueError("Value cannot contain newline or tab characters")

    return value


def validate_optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None
