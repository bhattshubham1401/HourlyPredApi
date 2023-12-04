from flask import Blueprint, request, jsonify

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
        id1 = todo_id + ":" + date
        query = {'_id': id}
        query1 = {'sensor_id': id1}

        todos = list(collection_name.find(query, {'_id': 0, 'data': 1}))
        todos_act = list(collection_name1.find(query1, {'_id': 0, 'data': 1}))
        formatted_data = {"data": []}
        for key, value in todos[0]["data"].items():
            formatted_data["data"].append(value)
        payLoad = {"datas": formatted_data["data"]}

        for key, value in todos_act[0]["data"].items():
            formatted_data["data"].append(value)
        payLoad1 = {"datas": formatted_data["data"]}

        return jsonify(payLoad), jsonify(payLoad1)


    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500


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
