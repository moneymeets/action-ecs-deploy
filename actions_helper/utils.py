from typing import Optional

PLACEHOLDER_TEXT = "PLACEHOLDER"


def set_error(message: str, file: Optional[str] = None, line: Optional[str] = None):
    print(f"::error {f'file={file}' if file else ''}{f',line={line}' if line else ''}::{message}")
    exit(1)
