"""Stage A SQLite storage primitives for the RED technical exercise."""

from . import provisioning


create_schema = provisioning.create_schema
seed_reference_data = provisioning.seed_reference_data

__all__ = ["create_schema", "seed_reference_data"]
