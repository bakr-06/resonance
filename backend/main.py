from fastapi import FastAPI

from routes.create_entry import router as create_entry_router

app = FastAPI()
app.include_router(create_entry_router)


@app.get("/")
async def root():
    return {"message": "Hello World"}
