from sqlmodel import create_engine, Session
from config import config

engine = create_engine(config.database_url)

def get_session():
    with Session(engine) as session:
        yield session  
