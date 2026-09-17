from sqlalchemy import ForeignKeyConstraint, Index


def child_household_foreign_key(constraint_name: str) -> ForeignKeyConstraint:
    return ForeignKeyConstraint(
        ["child_id", "household_id"],
        ["children.id", "children.household_id"],
        ondelete="CASCADE",
        name=constraint_name,
    )


def household_child_index(index_name: str) -> Index:
    return Index(index_name, "household_id", "child_id")
