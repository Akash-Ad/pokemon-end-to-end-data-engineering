import math
from pokepipeline.etl import transform_one

def sample_pokemon_payload():
    return {
        "id": 1,
        "name": "bulbasaur",
        "height": 7,             # decimetres -> 70 cm
        "weight": 69,            # hectograms -> 6.9 kg
        "base_experience": 64,
        "types": [
            {"slot": 1, "type": {"name": "grass",  "url": "https://pokeapi.co/api/v2/type/12/"}},
            {"slot": 2, "type": {"name": "poison", "url": "https://pokeapi.co/api/v2/type/4/" }},
        ],
        "abilities": [
            {"ability": {"name": "overgrow",     "url": "https://pokeapi.co/api/v2/ability/65/"},
             "is_hidden": False, "slot": 1},
            {"ability": {"name": "chlorophyll",  "url": "https://pokeapi.co/api/v2/ability/34/"},
             "is_hidden": True,  "slot": 3},
        ],
        "stats": [
            {"base_stat": 45, "effort": 0,
             "stat": {"name": "hp",     "url": "https://pokeapi.co/api/v2/stat/1/"}},
            {"base_stat": 49, "effort": 0,
             "stat": {"name": "attack", "url": "https://pokeapi.co/api/v2/stat/2/"}},
        ],
        "sprites": {"front_default": "https://example/img.png"},
    }

def test_transform_basic_units_and_bmi():
    raw = sample_pokemon_payload()
    t = transform_one(raw)

    assert t.id == 1
    assert t.name == "bulbasaur"
    assert t.base_experience == 64

    assert t.height_cm == 70
    assert math.isclose(t.weight_kg, 6.9, rel_tol=1e-6)
    assert t.bmi is not None and t.bmi > 0

    type_names = [name for (_id, name, _slot) in t.types]
    assert {"grass", "poison"}.issubset(set(type_names))

    ability_names = [name for (_id, name, _hidden, _slot) in t.abilities]
    assert {"overgrow", "chlorophyll"}.issubset(set(ability_names))

    stat_names = [name for (_id, name, _base, _eff) in t.stats]
    assert "hp" in stat_names