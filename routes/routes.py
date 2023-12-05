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
        query = {'_id': id}

        todos_pred = list(collection_name.find(query, {'_id': 0, 'data': 1}))
        todos_act = list(collection_name1.find(query, {'_id': 0, 'data': 1}))
        if not todos_act:
            # Actual data not found, create zero values for each hour
            zero_values = {"act_kwh": 0.0}
            actual_data = [zero_values.copy() for _ in range(24)]
        else:
            # Actual data found, extract values from the data
            formatted_data_act = {"data_act": {}}
            for key, value in todos_act[0]["data"].items():
                formatted_data_act["data_act"][key] = value
            actual_data = formatted_data_act

        formatted_data_pred = {"data_pred": {}}
        for key, value in todos_pred[0]["data"].items():
            formatted_data_pred["data_pred"][key] = value

        return {"predicted_data": formatted_data_pred, "actual_data": actual_data}

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
