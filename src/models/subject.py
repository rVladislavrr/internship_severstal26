from sqlalchemy.orm import mapped_column, Mapped

from src.models import Base


class SubjectsORM(Base):
    __tablename__ = 'subjects'

    id: Mapped[int] = mapped_column(
        primary_key=True,
        unique=True,
        comment='Айди объекта'
    )

    length: Mapped[float] = mapped_column(
        nullable=False,
        comment='Длинна объекта'
    )

    weight: Mapped[float] = mapped_column(
        nullable=False,
        comment='Вес объекта'
    )

    is_active: Mapped[bool] = mapped_column(
        nullable=False,
        comment='Удалён ли объект',
        default=True,
        index=True
    )