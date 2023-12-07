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

        # Check if actual data exists
        todos_act = list(collection_name1.find(query, {'_id': 0, 'data': 1}))
        if not todos_act:
            # Actual data not found, create an array of zeros for each hour
            actual_data = {"data_act": [{"act_kwh": 0.0} for _ in range(24)]}
        else:
            # Actual data found, extract values from the data
            formatted_data_act = {"data_act": []}
            for key, value in todos_act[0]["data"].items():
                formatted_data_act["data_act"].append({"act_kwh": value["act_kwh"]})
            actual_data = formatted_data_act

        # Check if predicted data exists
        todos_pred = list(collection_name.find(query, {'_id': 0, 'data': 1}))
        if not todos_pred:
            # Predicted data not found, create an array of zeros for each hour
            predicted_data = {"data_pred": [{"pred_kwh": 0.0} for _ in range(24)]}
        else:
            # Predicted data found, extract values from the data
            formatted_data_pred = {"data_pred": []}
            for key, value in todos_pred[0]["data"].items():
                formatted_data_pred["data_pred"].append({"pred_kwh": value["pred_kwh"]})
            predicted_data = formatted_data_pred

        return {"actual_data": actual_data, "predicted_data": predicted_data}

    except Exception as e:
        return {"error": str(e)}




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
