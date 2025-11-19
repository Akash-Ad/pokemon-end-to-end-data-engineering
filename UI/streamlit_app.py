"""
This Streamlit app serves as the frontend for the PokePipeline, allowing users to run the ETL process and explore the loaded Pokémon data.
"""
from __future__ import annotations
import streamlit as st
from typing import List, Dict
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from pokepipeline.db import create_schema, session_scope, drop_schema
from pokepipeline.pipeline import run_etl
from pokepipeline.models import Pokemon, Type, Ability, PokemonType, PokemonAbility


# Helper functions for database queries and data formatting
def get_all_types(session: Session) -> List[str]:
    """Returns a sorted list of all type names in the database."""
    rows = session.execute(select(Type.name)).scalars().all()
    return sorted(rows)


def fetch_pokemon(
    session: Session,
    name_query: str | None = None,
    types_filter: List[str] | None = None,
) -> List[Dict]:
    """
    Returns Pokemon rows with aggregated types/abilities and sprite URL.
    Filters can be applied by name (icontains) and by types (any match).
    """
    # Base rows
    pokes = session.execute(select(Pokemon)).scalars().all()
    # Early exit if nothing is in the DB
    if not pokes:
        return []

    # Preload type and ability links to avoid N+1 joins.
    pt_rows = session.execute(
        select(PokemonType.pokemon_id, Type.name)
        .join(Type, PokemonType.type_id == Type.id)
    ).all()
    pa_rows = session.execute(
        select(PokemonAbility.pokemon_id, Ability.name, PokemonAbility.is_hidden)
        .join(Ability, PokemonAbility.ability_id == Ability.id)
    ).all()

    # Build lookup maps
    type_map: Dict[int, List[str]] = {}
    for pid, tname in pt_rows:
        type_map.setdefault(pid, []).append(tname)

    ability_map: Dict[int, List[str]] = {}
    for pid, aname, is_hidden in pa_rows:
        label = f"{aname} (hidden)" if is_hidden else aname
        ability_map.setdefault(pid, []).append(label)

    # Build records
    data: List[Dict] = []
    for p in pokes:
        rec = {
            "id": p.id,
            "name": p.name,
            "types": ", ".join(sorted(type_map.get(p.id, []))),
            "abilities": ", ".join(sorted(ability_map.get(p.id, []))),
            "height_cm": p.height_cm,
            "weight_kg": p.weight_kg,
            "bmi": round(p.bmi, 2) if p.bmi else None,
            "base_experience": p.base_experience,
            "sprite_url": p.sprite_url,
        }
        data.append(rec)

    # Apply filters
    if name_query:
        q = name_query.strip().lower()
        data = [d for d in data if q in d["name"].lower()]

    if types_filter:
        selected = set(t.lower() for t in types_filter)
        data = [
            d for d in data
            if any(t.strip().lower() in selected for t in d["types"].split(",") if t.strip())
        ]

    # Sort by id for stable display
    data.sort(key=lambda d: d["id"])
    return data


# Streamlit layout and user interactions
st.set_page_config(page_title="PokePipeline", layout="wide")

st.title("Pokemon Pipeline")
st.caption("Etract → Transform → Load Pokemon data, then browse it.")

# Ensure schema exists (safe to call repeatedly).
create_schema()

with st.sidebar:
    st.subheader("Run ETL Pipeline")
    limit = st.number_input("Limit", min_value=1, max_value=200, value=20, step=1)
    offset = st.number_input("Offset (starting index)", min_value=0, max_value=10000, value=0, step=10)
    run = st.button("Run")

    st.subheader("Database Actions")
    if st.button("Clear database"):
        drop_schema()
        create_schema()
        # Ensure the view starts fresh after clearing data
        st.session_state["page"] = 1
        st.warning("Database cleared. Run the ETL to load data.")

    if run:
        requested, loaded = run_etl(limit=int(limit), offset=int(offset))
        st.success(f"ETL complete: requested={requested}, loaded={loaded}")

# Filters row
with session_scope() as session:
    all_types = get_all_types(session)

col1, col2 = st.columns([2, 2])
with col1:
    name_query = st.text_input("Search by name")
with col2:
    selected_types = st.multiselect("Filter by type", options=all_types)

# Data table
with session_scope() as session:
    rows = fetch_pokemon(session, name_query=name_query, types_filter=selected_types)

if not rows:
    st.info("No Pokemon found in the database yet. Use the sidebar to run the ETL.")
else:
    # Grid view with images and key stats
    st.write(f"Showing {len(rows)} Pokemon")
    for r in rows:
        with st.container():
            cols = st.columns([1, 2, 2, 1.5, 1.5, 1.5, 2.5])
            with cols[0]:
                if r["sprite_url"]:
                    st.image(r["sprite_url"], width=64)
            with cols[1]:
                st.markdown(f"**#{r['id']} — {r['name'].title()}**")
                st.caption(r["types"])
            cols[2].metric("Base XP", r["base_experience"])
            cols[3].metric("Height (cm)", r["height_cm"])
            cols[4].metric("Weight (kg)", r["weight_kg"])
            cols[5].metric("BMI", r["bmi"] if r["bmi"] is not None else "-")
            with cols[6]:
                st.caption(f"Abilities: {r['abilities']}")
            st.divider()