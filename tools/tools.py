from tools.sql_db import sql_tools
from tools.vector_db import parking_kb_retrieve
from tools.book_space import book_parking_space

tools = sql_tools() + [
    parking_kb_retrieve,
    book_parking_space,
]
