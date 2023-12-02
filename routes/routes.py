from flask import Blueprint, request
from config.db import collection_name

router = Blueprint('router', __name__)


# GET request
@router.route('/getPredData', methods=['GET'])
def get_todos():
    # Access parameters from the query string
    todo_id = request.args.get('id')
    date = request.args.get('date')

    # Concatenate todo_id and date to create a new identifier
    id = todo_id + "_" + date
    query = {'_id': id}, {'data': 1}

    todos = list(collection_name.find(query))
    return todos

