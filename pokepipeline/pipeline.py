"""
Orchestration is handled in this module. It is used by both the CLI and the Streamlit app.
""" 
from __future__ import annotations
import asyncio
from typing import Tuple
from .db import session_scope, create_schema
from .etl import extract_transform, load_batch


def run_etl(limit: int = 20, offset: int = 0) -> Tuple[int, int]:
    """
    Execute the ETL for a page of Pokemon.
    Returns a tuple: (requested, loaded).
    """
    create_schema()  # creates tables if missing; calling again has no effect

    items = asyncio.run(extract_transform(limit=limit, offset=offset))
    with session_scope() as session:
        loaded = load_batch(session, items)
    return (len(items), loaded)