import re

import pandas as pd
from sqlalchemy import inspect, select
from sqlalchemy.orm import as_declarative, declared_attr

from databall.db.session import Session


@as_declarative()
class Base:
    @declared_attr
    def __tablename__(cls):
        return re.sub(r'([a-z\d])([A-Z])', r'\1_\2', cls.__name__).lower()

    @classmethod
    def populate(cls, *args, **kwargs):
        raise NotImplementedError(
            f'Method populate not implemented for table {cls.__tablename__}'
        )

    @classmethod
    @property
    def primary_keys(cls):
        with Session() as session, session.connection() as connection:
            columns = inspect(cls).primary_key
            query = select(columns)
            df = pd.read_sql(query, connection)

        return df

    @classmethod
    def save_df(cls, df):
        df_primary = cls.primary_keys
        df_primary.columns = df_primary.columns.str.upper()

        columns = list(df_primary.columns)
        df_save = df.merge(df_primary, how='left', on=columns, indicator=True)
        df_save = df_save[df_save._merge == 'left_only']

        if df_save.empty:
            print(f'All primary keys already in {cls.__tablename__}')
            return

        columns = {column.upper() for column in cls.__table__.columns.keys()}
        columns_to_drop = set(df_save.columns) - columns
        df_save = df_save.drop(columns_to_drop, axis=1)

        with Session() as session:
            engine = session.get_bind()
            df_save.to_sql(cls.__tablename__, engine, if_exists='append', index=False)

        print(f'Saved {len(df_save)} rows to {cls.__tablename__}')
