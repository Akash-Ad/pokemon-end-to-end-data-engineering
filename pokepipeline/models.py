"""
Database tables are defined here using SQLAlchemy ORM.
The schema reflects the mapping decisions documented in the README.
"""
from __future__ import annotations
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Shared declarative base for all models."""


class Pokemon(Base):
    __tablename__ = "pokemon"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    base_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Units: cm for height; kg for weight. BMI is derived at transform time.
    height_cm: Mapped[int] = mapped_column(Integer, nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    bmi: Mapped[float | None] = mapped_column(Float, nullable=True)

    sprite_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    loaded_at: Mapped[str] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )

    types: Mapped[list["PokemonType"]] = relationship(
        back_populates="pokemon", cascade="all, delete-orphan"
    )
    abilities: Mapped[list["PokemonAbility"]] = relationship(
        back_populates="pokemon", cascade="all, delete-orphan"
    )
    stats: Mapped[list["PokemonStat"]] = relationship(
        back_populates="pokemon", cascade="all, delete-orphan"
    )


class Type(Base):
    __tablename__ = "type"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    pokemons: Mapped[list["PokemonType"]] = relationship(back_populates="type")


class Ability(Base):
    __tablename__ = "ability"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    pokemons: Mapped[list["PokemonAbility"]] = relationship(back_populates="ability")


class Stat(Base):
    __tablename__ = "stat"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    pokemons: Mapped[list["PokemonStat"]] = relationship(back_populates="stat")


class PokemonType(Base):
    __tablename__ = "pokemon_type"
    __table_args__ = (UniqueConstraint("pokemon_id", "type_id", name="uq_pokemon_type"),)

    pokemon_id: Mapped[int] = mapped_column(
        ForeignKey("pokemon.id", ondelete="CASCADE"), primary_key=True
    )
    type_id: Mapped[int] = mapped_column(
        ForeignKey("type.id", ondelete="CASCADE"), primary_key=True
    )
    slot: Mapped[int] = mapped_column(Integer, nullable=False)

    pokemon: Mapped["Pokemon"] = relationship(back_populates="types")
    type: Mapped["Type"] = relationship(back_populates="pokemons")


class PokemonAbility(Base):
    __tablename__ = "pokemon_ability"
    __table_args__ = (UniqueConstraint("pokemon_id", "ability_id", name="uq_pokemon_ability"),)

    pokemon_id: Mapped[int] = mapped_column(
        ForeignKey("pokemon.id", ondelete="CASCADE"), primary_key=True
    )
    ability_id: Mapped[int] = mapped_column(
        ForeignKey("ability.id", ondelete="CASCADE"), primary_key=True
    )
    is_hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    slot: Mapped[int] = mapped_column(Integer, nullable=False)

    pokemon: Mapped["Pokemon"] = relationship(back_populates="abilities")
    ability: Mapped["Ability"] = relationship(back_populates="pokemons")


class PokemonStat(Base):
    __tablename__ = "pokemon_stat"
    __table_args__ = (UniqueConstraint("pokemon_id", "stat_id", name="uq_pokemon_stat"),)

    pokemon_id: Mapped[int] = mapped_column(
        ForeignKey("pokemon.id", ondelete="CASCADE"), primary_key=True
    )
    stat_id: Mapped[int] = mapped_column(
        ForeignKey("stat.id", ondelete="CASCADE"), primary_key=True
    )
    base_stat: Mapped[int] = mapped_column(Integer, nullable=False)
    effort: Mapped[int] = mapped_column(Integer, nullable=False)

    pokemon: Mapped["Pokemon"] = relationship(back_populates="stats")
    stat: Mapped["Stat"] = relationship(back_populates="pokemons")