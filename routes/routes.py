from datetime import datetime

from flask import Blueprint, request

from config.db import collection_name, collection_name1

router = Blueprint('router', __name__)


# GET request
@router.route('/getPredData', methods=['GET'])
def get_todos():
    try:
        # Access parameters from the query string
        todo_id = request.args.get('id')
        date = request.args.get('date')

        # Concatenate todo_id and date to create a new identifier
        id = todo_id + "_" + date
        query = {'_id': id}

        todos = list(collection_name.find(query, {'_id': 0, 'data': 1}))
        return todos
    except Exception as e:
        print(e)


@router.route('/getActualData', methods=['POST'])
async def get_actual_data(id: str, date: str):
    try:
        start_date = datetime.strptime(date, '%Y-%m-%d')
        todos = list(collection_name1.find({
            'sensor_id': id,
            'Clock': start_date
        }))

        return todos
    except Exception as e:
        print(e)
