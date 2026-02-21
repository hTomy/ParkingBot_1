from fastapi import FastAPI, Request
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+psycopg2://user:password@localhost/dbname"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI()

@app.post("/mcp")
async def mcp_endpoint(request: Request):
    data = await request.json()
    # Example: Expecting {"action": "query", "sql": "SELECT * FROM users"}
    action = data.get("action")
    sql = data.get("sql")
    if action == "query" and sql:
        with SessionLocal() as session:
            result = session.execute(text(sql))
            rows = [dict(row) for row in result]
        return {"result": rows}
    return {"error": "Invalid request"}