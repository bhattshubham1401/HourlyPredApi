from flask import Blueprint, request

from config.db import collection_name

router = Blueprint('router', __name__)


# GET request
@router.route('/getPredDatas', methods=['GET'])
def get_todos():
    try:
        # Access parameters from the query string
        todo_id = request.args.get('id')
        date = request.args.get('date')

        # Concatenate todo_id and date to create a new identifier
        id = todo_id + "_" + date
        query = {'_id': id}

        todos = list(collection_name.find(query, {'_id': 0, 'data': 1}))
        formatted_data = {"data": []}
        for key, value in todos[0]["data"].items():
            formatted_data["data"].append(value)

        # Now, formatted_data has the structure you wanted
        payLoad = {"datas": formatted_data["data"]}

        return payLoad
    except Exception as e:
        print(e)


# @router.route('/getActualData', methods=['POST'])
# async def get_actual_data(id: str, date: str):
#     try:
#         start_date = datetime.strptime(date, '%Y-%m-%d')
#         todos = list(collection_name1.find({
#             'sensor_id': id,
#             'Clock': start_date
#         }))

    #     return todos
    # except Exception as e:
    #     print(e)
