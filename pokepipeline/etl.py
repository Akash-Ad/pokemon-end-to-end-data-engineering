"""
ETL helpers for the PokéPipeline.

Async functions are used for network operations to fetch data concurrently and reduce total runtime
when calling the public PokeAPI.
"""
from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session
from .config import HTTP_TIMEOUT_SECONDS, MAX_CONCURRENCY, MAX_RETRIES, POKEAPI_BASE
from .models import (
    Ability,
    Pokemon,
    PokemonAbility,
    PokemonStat,
    PokemonType,
    Stat,
    Type,
)

# This part is to extarct the data from the API
def _id_from_url(url: str) -> int:
    """Extract the trailing integer id from PokeAPI URLs like .../type/1/"""
    return int(url.rstrip("/").split("/")[-1])


async def _fetch_json(client: httpx.AsyncClient, url: str) -> Dict[str, Any]:
    # A small fetcher with simple retries
    last_exc: Exception | None = None
    for _ in range(MAX_RETRIES):
        try:
            resp = await client.get(url, timeout=HTTP_TIMEOUT_SECONDS)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # network or 5xx
            last_exc = exc
            await asyncio.sleep(0.5)
    assert last_exc is not None
    raise last_exc


async def fetch_pokemon_list(limit: int, offset: int = 0) -> List[Dict[str, Any]]:
    # Return list items from /pokemon?limit=&offset= with 'name' and 'url' keys.
    url = f"{POKEAPI_BASE}/pokemon?limit={limit}&offset={offset}"
    async with httpx.AsyncClient() as client:
        data = await _fetch_json(client, url)
        return data.get("results", [])


async def fetch_pokemon_details(names_or_urls: List[str]) -> List[Dict[str, Any]]:
    """Fetch /pokemon/{name|id} payloads concurrently."""
    sem = asyncio.Semaphore(MAX_CONCURRENCY)

    async def _one(target: str) -> Dict[str, Any]:
        async with sem:
            url = target if target.startswith("http") else f"{POKEAPI_BASE}/pokemon/{target}"
            async with httpx.AsyncClient() as client:
                return await _fetch_json(client, url)

    return await asyncio.gather(*(_one(t) for t in names_or_urls))


# This part is to perfrom transforamtion
@dataclass
class TPokemon:
    # A minimal, normalized view used by the loader
    id: int
    name: str
    base_experience: int | None
    height_cm: int
    weight_kg: float
    bmi: float | None
    sprite_url: str | None
    types: List[Tuple[int, str, int]]          # (type_id, type_name, slot)
    abilities: List[Tuple[int, str, bool, int]]  # (ability_id, name, is_hidden, slot)
    stats: List[Tuple[int, str, int, int]]     # (stat_id, name, base_stat, effort)


def _to_cm(dm: int) -> int:
    return int(dm * 10)


def _to_kg(hg: int) -> float:
    return hg / 10.0


def _bmi(height_cm: int, weight_kg: float) -> float | None:
    m = height_cm / 100.0
    return (weight_kg / (m * m)) if m > 0 else None


def transform_one(payload: Dict[str, Any]) -> TPokemon:
    pid = int(payload["id"])
    name = str(payload["name"])
    base_xp = payload.get("base_experience")
    height_cm = _to_cm(int(payload["height"]))
    weight_kg = _to_kg(int(payload["weight"]))
    bmi = _bmi(height_cm, weight_kg)
    sprite = payload.get("sprites", {}).get("front_default")

    types: List[Tuple[int, str, int]] = []
    for t in payload.get("types", []):
        t_name = t["type"]["name"]
        t_id = _id_from_url(t["type"]["url"])
        types.append((t_id, t_name, int(t["slot"])))

    abilities: List[Tuple[int, str, bool, int]] = []
    for a in payload.get("abilities", []):
        a_name = a["ability"]["name"]
        a_id = _id_from_url(a["ability"]["url"])
        abilities.append((a_id, a_name, bool(a["is_hidden"]), int(a["slot"])))

    stats: List[Tuple[int, str, int, int]] = []
    for s in payload.get("stats", []):
        s_name = s["stat"]["name"]
        s_id = _id_from_url(s["stat"]["url"])
        stats.append((s_id, s_name, int(s["base_stat"]), int(s["effort"])))

    return TPokemon(
        id=pid,
        name=name,
        base_experience=base_xp,
        height_cm=height_cm,
        weight_kg=weight_kg,
        bmi=bmi,
        sprite_url=sprite,
        types=types,
        abilities=abilities,
        stats=stats,
    )


# This part is to load data
def upsert_reference_batch(session: Session, batch: List[TPokemon]) -> None:
    """Insert/update unique Type/Ability/Stat rows once per batch to avoid PK conflicts."""
    type_map: dict[int, str] = {}
    ability_map: dict[int, str] = {}
    stat_map: dict[int, str] = {}

    for tp in batch:
        for type_id, type_name, _slot in tp.types:
            type_map[type_id] = type_name
        for ability_id, ability_name, _hidden, _slot in tp.abilities:
            ability_map[ability_id] = ability_name
        for stat_id, stat_name, _base, _effort in tp.stats:
            stat_map[stat_id] = stat_name

    for tid, name in type_map.items():
        session.merge(Type(id=tid, name=name))
    for aid, name in ability_map.items():
        session.merge(Ability(id=aid, name=name))
    for sid, name in stat_map.items():
        session.merge(Stat(id=sid, name=name))


def upsert_pokemon(session: Session, tp: TPokemon) -> None:
    """Upsert core pokemon row and all junction rows."""
    session.merge(
        Pokemon(
            id=tp.id,
            name=tp.name,
            base_experience=tp.base_experience,
            height_cm=tp.height_cm,
            weight_kg=tp.weight_kg,
            bmi=tp.bmi,
            sprite_url=tp.sprite_url,
        )
    )

    # Junctions (composite PKs make this idempotent with merge)
    for type_id, _name, slot in tp.types:
        session.merge(PokemonType(pokemon_id=tp.id, type_id=type_id, slot=slot))

    for ability_id, _name, is_hidden, slot in tp.abilities:
        session.merge(
            PokemonAbility(
                pokemon_id=tp.id,
                ability_id=ability_id,
                is_hidden=is_hidden,
                slot=slot,
            )
        )

    for stat_id, _name, base_stat, effort in tp.stats:
        session.merge(
            PokemonStat(
                pokemon_id=tp.id,
                stat_id=stat_id,
                base_stat=base_stat,
                effort=effort,
            )
        )

# Pipeline entry points
async def extract_transform(limit: int, offset: int = 0) -> List[TPokemon]:
    """Fetch a page of Pokémon and return transformed items."""
    listing = await fetch_pokemon_list(limit=limit, offset=offset)
    targets = [item["name"] for item in listing]
    details = await fetch_pokemon_details(targets)
    return [transform_one(p) for p in details]


def load_batch(session: Session, batch: list[TPokemon]) -> int:
    """Loads a batch of Pokémon records into the database and returns the number processed."""    
    upsert_reference_batch(session, batch)
    for tp in batch:
        upsert_pokemon(session, tp)
    return len(batch)