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
        id = f"{todo_id}_{date}"
        id1 = f"{todo_id}:{date}"

        query = {'_id': id}
        query1 = {'sensor_id': id1}

        todos = list(collection_name.find(query, {'_id': 0, 'data': 1}))
        todos_act = list(collection_name1.find(query1, {'_id': 0, 'data': 1}))

        formatted_data = {"data": []}

        # Check if lists are not empty before accessing elements
        if todos:
            for key, value in todos[0]["data"].items():
                formatted_data["data"].append(value)

        payLoad = {"datas": formatted_data["data"]}

        if todos_act:
            for key, value in todos_act[0]["data"].items():
                formatted_data["data"].append(value)

        payLoad1 = {"datas": formatted_data["data"]}

        # Combine the data into a single response
        combined_payload = {"payloads": [payLoad, payLoad1]}

        return jsonify(combined_payload)

    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500  # Return an error response
