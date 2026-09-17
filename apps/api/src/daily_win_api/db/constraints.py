from sqlalchemy import ForeignKeyConstraint, Index, UniqueConstraint


def child_household_foreign_key(constraint_name: str) -> ForeignKeyConstraint:
    return ForeignKeyConstraint(
        ["child_id", "household_id"],
        ["children.id", "children.household_id"],
        ondelete="CASCADE",
        name=constraint_name,
    )


def household_child_index(index_name: str) -> Index:
    return Index(index_name, "household_id", "child_id")


def id_child_household_unique(constraint_name: str) -> UniqueConstraint:
    return UniqueConstraint(
        "id", "child_id", "household_id", name=constraint_name
    )


def daily_win_child_household_foreign_key(
    constraint_name: str, *, ondelete: str = "RESTRICT"
) -> ForeignKeyConstraint:
    return ForeignKeyConstraint(
        ["daily_win_id", "child_id", "household_id"],
        ["daily_wins.id", "daily_wins.child_id", "daily_wins.household_id"],
        ondelete=ondelete,
        name=constraint_name,
    )
