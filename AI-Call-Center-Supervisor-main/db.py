# db.py
import os
from sqlalchemy import (Column, Integer, String, Text, DateTime, Boolean, create_engine, MetaData, Table)
from sqlalchemy.sql import func
from databases import Database

DB_URL = os.getenv('DATABASE_URL', 'sqlite:///./callcenter.db')

database = Database(DB_URL)
metadata = MetaData()

conversations = Table(
    'conversations', metadata,
    Column('id', Integer, primary_key=True),
    Column('agent_name', String(128), nullable=False),
    Column('created_at', DateTime, server_default=func.now()),
)

messages = Table(
    'messages', metadata,
    Column('id', Integer, primary_key=True),
    Column('conversation_id', Integer, nullable=False),
    Column('role', String(20)),
    Column('content', Text),
    Column('created_at', DateTime, server_default=func.now()),
)

resolved_facts = Table(
    'resolved_facts', metadata,
    Column('id', Integer, primary_key=True),
    Column('conversation_id', Integer, nullable=False),
    Column('fact_key', String(128)),
    Column('fact_value', String(512)),
    Column('confirmed', Boolean, default=False),
    Column('created_at', DateTime, server_default=func.now()),
)

engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if 'sqlite' in DB_URL else {})

def init_db():
    metadata.create_all(engine)
