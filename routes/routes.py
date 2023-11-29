from fastapi import APIRouter
from Models.todos import Todo
from config.db import collection_name
from schema.schemas import list_serial

router = APIRouter()

# GET request
@router.get("/")
async def get_todos():
    todos = list_serial(collection_name.find())
    return todos

# @router.post("/")
# async def post_todo(todo : Todo):
#     collection_name.insert_one(dict(todo))


