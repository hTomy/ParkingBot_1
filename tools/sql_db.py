from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit

from sqlalchemy import create_engine

from utils import config

def sql_tools():
    llm = ChatOpenAI(model=config.MODEL, temperature=0)

    engine = create_engine(config.POSTGRES_URI)
    db = SQLDatabase(engine, include_tables=["parking_bookings"])
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    sql_tools = toolkit.get_tools()

    return sql_tools