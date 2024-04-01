from calendar import monthrange

from flask import Blueprint, request, jsonify

from config.db import collection_name, collection_name1, collection_name2, collection_name3, collection_name4, collection_name5, collection_name6, collection_name7, collection_name8
router = Blueprint('router', __name__)
import requests
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import traceback



@router.route('/get_sensorList', methods=['GET'])
def get_sensorList():
    try:
        # sensor_ids = ['5f718b613291c7.03696209',
        #               '5f718c439c7a78.65267835',
        #               '614366bce31a86.78825897',
        #               '6148740eea9db0.29702291',
        #               '625fb44c5fb514.98107900',
        #               '625fb9e020ff31.33961816',
        #               '6260fd4351f892.69790282',
        #               '627cd4815f2381.31981050',
        #               '629094ee5fdff4.43505210',
        #               '62aad7f5c65185.80723547',
        #               '62b15dfee341d1.73837476',
        #               '62b595eabd9df4.71374208',
        #               '6349368c306542.16235883',
        #               '634e7c43038801.39310596',
        #               '6399a18b1488b8.07706749',
        #               '63a4195534d625.00718490',
        #               '63a4272631f153.67811394',
        #               '63aa9161b9e7e1.16208626',
        #               '63ca403ccd66f3.47133508',
        #               '62a9920f75c931.62399458']
        sensor_ids = [
            '5f718b613291c7.03696209',
            '5f718c439c7a78.65267835',
            '6148740eea9db0.29702291',
            '625fb44c5fb514.98107900',
            '625fb9e020ff31.33961816',
            '6260fd4351f892.69790282',
            '627cd4815f2381.31981050',
            '629094ee5fdff4.43505210',
            '62b15dfee341d1.73837476',
            '634e7c43038801.39310596',
            '6399a18b1488b8.07706749',
            '63a4195534d625.00718490',
            '63a4272631f153.67811394',
            '62a9920f75c931.62399458',
            '62aad7f5c65185.80723547',
            '63aa9161b9e7e1.16208626',
            '63ca403ccd66f3.47133508'
        ]

        url = "https://vapt-npcl.myxenius.com/Sensor_newHelper/getDataApi"
        params = {

            'sql': "SELECT id AS uuid, name AS sensorName, CASE WHEN grid_billing_type IS NOT NULL THEN grid_billing_type ELSE 'UOM' END AS uom FROM sensor WHERE id IN ({}) ORDER BY name".format(
                ','.join(f"'{sid}'" for sid in sensor_ids)),

            'type': 'query'
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        sensor_list = [{'uuid': item['uuid'], 'sensorName': item['sensorName'], "UOM": item['uom']} for item in
                       data['resource']]
        return jsonify({"rc": 0, "message": "Success", 'sensorList': sensor_list})

    except Exception as e:
        print(e)
        return jsonify({"rc": -1, "message": "error"}), 500


@router.route('/getPredDataHourly', methods=['GET'])
def getPredDataHourly():
    try:
        # Access parameters from the query string
        todo_id = request.args.get('id')
        date = request.args.get('date')

        # Concatenate todo_id and date to create a new identifier
        id = todo_id + "_" + date
        query = {'_id': id}

        # Check if actual data exists
        l1 = []
        url = "https://vapt-npcl.myxenius.com/Sensor_newHelper/getDataApi"
        params = {
            'sql': "select raw_data, sensor_id, read_time from dlms_load_profile where sensor_id='{}' and date(read_time)='{}' order by read_time"
            .format(todo_id, date),
            'type': 'query'
        }
        todos_act = requests.get(url, params=params)
        todos_act.raise_for_status()
        data = todos_act.json()
        l1.append(data['resource'])

        columns = ['sensor', 'Clock', 'R_Voltage', 'Y_Voltage', 'B_Voltage', 'R_Current', 'Y_Current',
                   'B_Current', 'A', 'BlockEnergy-WhExp', 'B', 'C', 'D', 'BlockEnergy-VAhExp',
                   'Kwh', 'BlockEnergy-VArhQ1', 'BlockEnergy-VArhQ4', 'BlockEnergy-VAhImp']

        datalist = [(entry['sensor_id'], entry['raw_data']) for i in range(len(l1)) for entry in l1[i]]

        df = pd.DataFrame([row[0].split(',') + row[1].split(',') for row in datalist], columns=columns)

        df = df.drop([
            'R_Voltage', 'Y_Voltage', 'B_Voltage', 'R_Current', 'Y_Current',
            'B_Current', 'A', 'BlockEnergy-WhExp', 'B', 'C', 'D', 'BlockEnergy-VAhExp',
            'BlockEnergy-VArhQ1', 'BlockEnergy-VArhQ4', 'BlockEnergy-VAhImp'], axis=1)
        pd.set_option('display.max_columns', None)
        df['Clock'] = pd.to_datetime(df['Clock'])
        df['Kwh'] = df['Kwh'].astype(float)
        df['Kwh'] = (df['Kwh'] / 1000)
        df.set_index(["Clock"], inplace=True, drop=True)
        df1 = (df[['Kwh']].resample(rule="1H").sum()).round(2)

        if not todos_act:
            # Actual data not found, create an array of zeros for each hour
            actual_data = {"data_act": [{"hour": hour, "act_kwh": 0.0} for hour in range(24)]}
        else:
            # max_demand=df1['Kwh'].max()
            # max_demand_time=df1.loc[df1['Kwh'].idxmax()]
            # max_kwh_hour = max_demand_time.name.hour
            # Actual data found, extract values from the data
            formatted_data_act = {"data_act": []}
            actal_hour_counter, actual_Kwh_sum = 0, 0
            for value in df1["Kwh"]:
                formatted_data_act["data_act"].append({"hour": actal_hour_counter, "act_kwh": value})
                actual_Kwh_sum += value
                actal_hour_counter += 1
            if (len(formatted_data_act['data_act'])) < 24:

                for i in range((len(formatted_data_act['data_act'])), 24):
                    formatted_data_act["data_act"].append({"hour": i, "act_kwh": 0.0})
            # max_demand=df1['Kwh'].max()
            # max_demand_time=df1.loc[df1['Kwh'].idxmax()]
            # max_kwh_hour = max_demand_time.name.hour
            actual_data = formatted_data_act
            max_value_dict = max(actual_data['data_act'], key=lambda x: x['act_kwh'])
            actual_max_hour = str(max_value_dict['hour']).zfill(2)
            actual_max_value = round(max_value_dict['act_kwh'], 2)
            # print(actual_data)
        # Check if predicted data exists
        todos_pred = list(collection_name.find(query, {'_id': 0, 'data': 1}))
        if not todos_pred:
            # Predicted data not found, create an array of zeros for each hour
            predicted_data = {"data_pred": [{"hour": hour, "pre_kwh": 0.0} for hour in range(24)]}

        else:
            # Predicted data found, extract values from the data
            formatted_data_pred = {"data_pred": []}
            pred_hour_counter, pred_daily_sum = 0, 0
            for key, value in todos_pred[0]["data"].items():
                formatted_data_pred["data_pred"].append(
                    {"hour": pred_hour_counter, "pre_kwh": round(value["pre_kwh"], 2)})
                pred_daily_sum += (value["pre_kwh"])
                pred_hour_counter += 1

            predicted_data = formatted_data_pred
            max_value_dict = max(predicted_data['data_pred'], key=lambda x: x['pre_kwh'])
            pred_max_hour = str(max_value_dict['hour']).zfill(2)
            pred_max_value = round(max_value_dict['pre_kwh'], 2)

        # Combine actual and predicted data into a single dictionary
        response_data = {"actual_data": actual_data["data_act"], "predicted_data": predicted_data["data_pred"]}

        return {"rc": 0, "message": "Success", "actual_kwh_sum": round(actual_Kwh_sum, 2),
                # "actual_max_demand":max_demand,"actual_max_kwh_hour":max_kwh_hour,
                "actual_max_hour": actual_max_hour, "actual_max_value": actual_max_value,
                "pred_max_hour": pred_max_hour, "pred_max_value": pred_max_value,
                "pred_daily_sum": round(pred_daily_sum, 2), "data": response_data}

    except Exception as e:
        return {"error": str(e)}


# @router.route('/getPredDataDaily', methods=['GET'])
# def getPredDataDaily():
#     try:
#         todo_id = request.args.get('id')
#         date = request.args.get('date')
#
#         date_object = datetime.strptime(date, '%Y-%m-%d')
#         first_date = date_object.replace(day=1)
#         day, month, year = first_date.day, first_date.month, first_date.year
#         last_date = (first_date.replace(month=first_date.month % 12 + 1, day=1, ) - timedelta(days=1))
#         last_date = last_date.replace(hour=23, minute=30, year=year)
#         last_day = last_date.day
#
#         query = {"sensor_id": todo_id, "month": str(month), "year": str(year)}
#
#         l1 = []
#         url = "https://multipoint.myxenius.com/Sensor_newHelper/getDataApi"
#         params = {
#             'sql': "select raw_data, sensor_id, read_time from dlms_load_profile where sensor_id='{}' and month(read_time)='{}' and year(read_time)='{}' order by read_time"
#             .format(todo_id, month, year),
#             'type': 'query'
#         }
#         todos_act = requests.get(url, params=params)
#         todos_act.raise_for_status()
#         data = todos_act.json()
#         l1.append(data['resource'])
#
#         columns = ['sensor', 'Clock', 'R_Voltage', 'Y_Voltage', 'B_Voltage', 'R_Current', 'Y_Current',
#                    'B_Current', 'A', 'BlockEnergy-WhExp', 'B', 'C', 'D', 'BlockEnergy-VAhExp',
#                    'Kwh', 'BlockEnergy-VArhQ1', 'BlockEnergy-VArhQ4', 'BlockEnergy-VAhImp']
#
#         datalist = [(entry['sensor_id'], entry['raw_data']) for i in range(len(l1)) for entry in l1[i]]
#
#         df = pd.DataFrame([row[0].split(',') + row[1].split(',') for row in datalist], columns=columns)
#         df = df.drop([
#             'R_Voltage', 'Y_Voltage', 'B_Voltage', 'R_Current', 'Y_Current',
#             'B_Current', 'A', 'BlockEnergy-WhExp', 'B', 'C', 'D', 'BlockEnergy-VAhExp',
#             'BlockEnergy-VArhQ1', 'BlockEnergy-VArhQ4', 'BlockEnergy-VAhImp'], axis=1)
#         pd.set_option('display.max_columns', None)
#         df['Clock'] = pd.to_datetime(df['Clock'])
#         df['Kwh'] = df['Kwh'].astype(float)
#         df['Kwh'] = (df['Kwh'] / 1000)
#
#         df['Clock'] = pd.to_datetime(df['Clock'])
#         df.set_index(["Clock"], inplace=True, drop=True)
#
#         df1 = (df[['Kwh']].resample(rule="1D").sum()).round(2)
#
#         if not todos_act:
#             # Actual data not found, create an array of zeros for each hour
#             actual_data = {"data_act": [{f"act_kwh{_}": 0.0} for _ in range(last_day)]}
#         else:
#             # Actual data found, extract values from the data
#             formatted_data_act = {"data_act": []}
#
#             for value in df1["Kwh"]:
#                 formatted_data_act["data_act"].append({"clock": f"{year}-{month}-{day}", "act_kwh": value})
#                 day += 1
#
#             if (len(formatted_data_act['data_act']) != last_day):
#                 for i in range((len(formatted_data_act['data_act'])), (last_day)):
#                     formatted_data_act["data_act"].append(
#                         {"clock": f"{year}-{month}-{str(day).zfill(2)}", f"act_kwh {i + 1}": 0.0})
#                     day += 1
#             actual_data = formatted_data_act
#
#             # Check if predicted data exists
#         todos_pred = list(collection_name.find(query, {'_id': 1, 'data': 1}))
#         if not todos_pred:
#             # Predicted data not found, create an array of zeros for each hour
#             predicted_data = {"data_pred": [{f"pre_kwh{_}": 0.0} for _ in range(1, (last_day + 1))]}
#         else:
#             # Predicted data found, extract values from the data
#             formatted_data_pred = {"data_pred": []}
#             for i in range(len(todos_pred)):
#                 b = todos_pred[i]['_id'].split("_")
#                 date2 = b[1]
#                 sum = 0
#                 for y in range(24):
#                     a = todos_pred[i]['data'][f"{y}"]['pre_kwh']
#                     sum = sum + a
#                 formatted_data_pred["data_pred"].append({"clock": date2, "pre_kwh": round(sum, 2)})
#             predicted_data = formatted_data_pred
#
#         # Combine actual and predicted data into a single dictionary
#         response_data = {"actual_data": actual_data["data_act"], "predicted_data": predicted_data["data_pred"]}
#
#         return {"rc": 0, "message": "Success", "data": response_data}
#
#     except Exception as e:
#         return {"error": str(e)}


@router.route('/getPredDataDaily', methods=['GET'])
def getPredDataDaily():
    try:
        # Access parameters from the query string
        todo_id = request.args.get('id')
        date = request.args.get('date')

        month_from_date = (datetime.strptime(date, '%Y-%m-%d')).month
        month_today = (datetime.now()).month

        # Concatenate todo_id and date to create a new identifier
        id = todo_id + "_" + date
        query = {'_id': id}

        start_date = datetime.strptime(date + " 00:00:00", "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
        end_date = datetime.strptime(date + " 23:59:59", "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")

        act_data = {
            "sensor_id": todo_id,
            "read_time": {"$gte": start_date, "$lt": end_date}
        }
        l1 = []
        # Check if actual data exist
        # for document in documents:
        #     # print()
        #     l1.append(document['resource'])
        # print("helkl")
        # print(l1)

        # url = "https://vapt-npcl.myxenius.com/Sensor_newHelper/getDataApi"
        # params = {
        #     'sql': "select raw_data, sensor_id, read_time from dlms_load_profile where sensor_id='{}' and date(read_time)='{}' order by read_time"
        #     .format(todo_id, date),
        #     'type': 'query'
        # }
        # todos_act = requests.get(url, params=params)
        # todos_act.raise_for_status()
        # data = todos_act.json()
        # l1.append(data['resource'])
        try:
            documents = collection_name4.find(act_data, {"raw_data": 1, "sensor_id": 1, "read_time": 1} )
            for document in documents:
                l1.append(document)
        except Exception as e:
            print("Error occurred while fetching documents:", e)

        columns = ['sensor', 'Clock', 'R_Voltage', 'Y_Voltage', 'B_Voltage', 'R_Current', 'Y_Current',
                   'B_Current', 'A', 'BlockEnergy-WhExp', 'B', 'C', 'D', 'BlockEnergy-VAhExp',
                   'Kwh', 'BlockEnergy-VArhQ1', 'BlockEnergy-VArhQ4', 'BlockEnergy-VAhImp']

        # datalist = [(entry['sensor_id'], entry['raw_data']) for i in range(len(l1)) for entry in l1[i]]
        # df = pd.DataFrame([row[0].split(',') + row[1].split(',') for row in datalist], columns=columns)
        datalist = [{'sensor': entry['sensor_id'], **dict(zip(columns[1:], entry['raw_data'].split(',')))} for entry in
                    l1]

        # Create DataFrame using the list of dictionaries and set columns
        df = pd.DataFrame(datalist, columns=columns)

        df = df.drop([
            'R_Voltage', 'Y_Voltage', 'B_Voltage', 'R_Current', 'Y_Current',
            'B_Current', 'A', 'BlockEnergy-WhExp', 'B', 'C', 'D', 'BlockEnergy-VAhExp',
            'BlockEnergy-VArhQ1', 'BlockEnergy-VArhQ4', 'BlockEnergy-VAhImp'], axis=1)
        pd.set_option('display.max_columns', None)
        df['Clock'] = pd.to_datetime(df['Clock'])
        df['Kwh'] = df['Kwh'].astype(float)
        df['Kwh'] = (df['Kwh'] / 1000)
        df.set_index(["Clock"], inplace=True, drop=True)
        df1 = (df[['Kwh']].resample(rule="1H").sum()).round(2)

        percent = 0.0
        act_daily_sum, actual_max_hour, actual_max_value = 0.0, "00", 0.0
        pred_daily_sum, pred_max_hour, pred_max_value = 0.0, "00", 0.0

        # actual data  storing
        formatted_data_act = {"data_act": []}
        if df1.empty is False:
            act_hour_counter = 0
            for value in df1["Kwh"]:
                formatted_data_act["data_act"].append({"clock": str(act_hour_counter).zfill(2), "act_kwh": value})
                act_daily_sum += value
                act_hour_counter += 1
            max_value_dict = max(formatted_data_act['data_act'], key=lambda x: x['act_kwh'])
            actual_max_hour = str(max_value_dict['clock']).zfill(2)
            actual_max_value = round(max_value_dict['act_kwh'], 2)

        if (len(formatted_data_act['data_act'])) < 24:
            for i in range((len(formatted_data_act['data_act'])), 24):
                formatted_data_act["data_act"].append({"clock": str(i).zfill(2), "act_kwh": 0.0})

        actual_data = formatted_data_act

        # Check if predicted data exists
        todos_pred = list(collection_name.find(query, {'_id': 0, 'data': 1}))

        formatted_data_pred = {"data_pred": []}
        if (len(todos_pred) != 0):
            # Predicted data found, extract values from the data
            pred_hour_counter = 0
            for key, value in todos_pred[0]["data"].items():
                formatted_data_pred["data_pred"].append(
                    {"clock": str(pred_hour_counter).zfill(2), "pre_kwh": round(value["pre_kwh"], 2)})
                pred_daily_sum += (value["pre_kwh"])
                pred_hour_counter += 1

            max_value_dict = max(formatted_data_pred['data_pred'], key=lambda x: x['pre_kwh'])
            pred_max_hour = str(max_value_dict['clock']).zfill(2)
            pred_max_value = round(max_value_dict['pre_kwh'], 2)

        # Predicted data not found or incomplete, create an array of zeros for each hour
        if (len(formatted_data_pred['data_pred'])) < 24:
            for i in range((len(formatted_data_pred['data_pred'])), 24):
                formatted_data_pred["data_pred"].append({"clock": str(i).zfill(2), "pre_kwh": 0.0})

        predicted_data = formatted_data_pred

        if ((month_from_date) != (month_today)) & (act_daily_sum != 0):
            percent = round(abs(((act_daily_sum - pred_daily_sum) / act_daily_sum) * 100), 2)

        # Combine actual and predicted data into a single dictionary
        response_data = {"actual_data": actual_data["data_act"], "predicted_data": predicted_data["data_pred"]}

        return {"rc": 0, "message": "Success",
                "actual_daily_sum": round(act_daily_sum, 2), "pred_daily_sum": round(pred_daily_sum, 2),
                "actual_max_hour": actual_max_hour, "actual_max_value": actual_max_value,
                "pred_max_hour": pred_max_hour, "pred_max_value": pred_max_value,
                "data": response_data,
                "percentage": percent}

    except Exception as e:
        return {"error": str(e)}


@router.route('/getPredDataMonthly', methods=['GET'])
def getPredDataMonthly():
    try:
        todo_id = request.args.get('id')
        date = request.args.get('date')

        month_today = (datetime.now()).month
        month = datetime.strptime(date, '%Y-%m').month
        year = datetime.strptime(date, '%Y-%m').year
        day = monthrange(year, month)
        last_day = day[1]

        query = {"sensor_id": todo_id, "month": str(month), "year": str(year)}
        print(query)

        l1 = []
        url = "https://vapt-npcl.myxenius.com/Sensor_newHelper/getDataApi"
        params = {
            'sql': "select raw_data, sensor_id, read_time from dlms_load_profile where sensor_id='{}' and month(read_time)='{}' and year(read_time)='{}' order by read_time"
            .format(todo_id, month, year),
            'type': 'query'
        }
        todos_act = requests.get(url, params=params)
        todos_act.raise_for_status()
        data = todos_act.json()
        l1.append(data['resource'])

        columns = ['sensor', 'Clock', 'R_Voltage', 'Y_Voltage', 'B_Voltage', 'R_Current', 'Y_Current',
                   'B_Current', 'A', 'BlockEnergy-WhExp', 'B', 'C', 'D', 'BlockEnergy-VAhExp',
                   'Kwh', 'BlockEnergy-VArhQ1', 'BlockEnergy-VArhQ4', 'BlockEnergy-VAhImp']

        datalist = [(entry['sensor_id'], entry['raw_data']) for i in range(len(l1)) for entry in l1[i]]

        df = pd.DataFrame([row[0].split(',') + row[1].split(',') for row in datalist], columns=columns)
        df = df.drop([
            'R_Voltage', 'Y_Voltage', 'B_Voltage', 'R_Current', 'Y_Current',
            'B_Current', 'A', 'BlockEnergy-WhExp', 'B', 'C', 'D', 'BlockEnergy-VAhExp',
            'BlockEnergy-VArhQ1', 'BlockEnergy-VArhQ4', 'BlockEnergy-VAhImp'], axis=1)
        pd.set_option('display.max_columns', None)
        df['Clock'] = pd.to_datetime(df['Clock'])
        df['Kwh'] = df['Kwh'].astype(float)
        df['Kwh'] = (df['Kwh'] / 1000)

        df['Clock'] = pd.to_datetime(df['Clock'])
        df.set_index(["Clock"], inplace=True, drop=True)

        df1 = (df[['Kwh']].resample(rule="1D").sum()).round(2)

        percent = 0.0
        act_monthly_sum, act_max_date, act_max_date_value = 0.0, f"{year}-{str(month).zfill(2)}-01", 0.0
        pred_monthly_sum, pred_max_date, pred_max_date_value = 0.0, f"{year}-{str(month).zfill(2)}-01", 0.0

        formatted_data_act = {"data_act": []}
        first_day = 1
        if df1.empty is False:
            # Actual data found, extract values from the data
            for value in df1["Kwh"]:
                formatted_data_act["data_act"].append(
                    {"clock": f"{year}-{str(month).zfill(2)}-{str(first_day).zfill(2)}", "act_kwh": value})
                act_monthly_sum += value
                first_day += 1

            max_value_dict = max(formatted_data_act['data_act'], key=lambda x: x['act_kwh'])
            act_max_date = str(max_value_dict['clock'])
            act_max_date_value = round(max_value_dict['act_kwh'], 2)

        if (len(formatted_data_act['data_act']) != last_day):
            for i in range((len(formatted_data_act['data_act']) + 1), (last_day + 1)):
                formatted_data_act["data_act"].append(
                    {"clock": f"{year}-{str(month).zfill(2)}-{str(first_day).zfill(2)}", "act_kwh": 0.0})
                first_day += 1

        actual_data = formatted_data_act

        # Check if predicted data exists
        todos_pred = list(collection_name.find(query, {'_id': 1, 'data': 1}))
        print(todos_pred)
        formatted_data_pred = {"data_pred": []}
        if (len(todos_pred)) != 0:
            # Predicted data found, extract values from the data
            for i in range(len(todos_pred)):
                b = todos_pred[i]['_id'].split("_")
                date2 = b[1]
                pred_daily_sum = 0
                for y in range(24):
                    a = todos_pred[i]['data'][f"{y}"]['pre_kwh']
                    pred_daily_sum += a
                formatted_data_pred["data_pred"].append({"clock": date2, "pre_kwh": round(pred_daily_sum, 2)})
                pred_monthly_sum += pred_daily_sum

            max_value_dict = max(formatted_data_pred['data_pred'], key=lambda x: x['pre_kwh'])
            pred_max_date = str(max_value_dict['clock'])
            pred_max_date_value = round(max_value_dict['pre_kwh'], 2)

        # Predicted data not found, create an array of zeros for each hour
        if len(todos_pred) != last_day:
            for _ in range(((len(todos_pred)) + 1), (last_day + 1)):
                formatted_data_pred['data_pred'].append(
                    {"clock": f"{year}-{str(month).zfill(2)}-{str(_).zfill(2)}", "pre_kwh": 0.0, })
        predicted_data = formatted_data_pred

        if ((month) != (month_today)) & (act_monthly_sum != 0.0):
            percent = round(abs(((act_monthly_sum - pred_monthly_sum) / act_monthly_sum) * 100), 2)

        # Combine actual and predicted data into a single dictionary
        response_data = {"actual_data": actual_data["data_act"], "predicted_data": predicted_data["data_pred"]}
        return {"rc": 0, "message": "Success",
                "act_max_date_value": act_max_date_value, "act_max_date": act_max_date,
                "pred_max_date_value": pred_max_date_value, "pred_max_date": pred_max_date,
                "act_monthly_sum": round(act_monthly_sum, 2), "pred_monthly_sum": round(pred_monthly_sum, 2),
                "percent": percent, "data": response_data}

    except Exception as e:
        return {"error": str(e)}

    """ These code is for experiments"""


@router.route('/getPredDataDaily1', methods=['GET'])
def getPredDataDaily1():
    try:
        # Access parameters from the query string
        # todo_id = request.args.get('id')
        # date = request.args.get('date')
        #
        # month_from_date = (datetime.strptime(date, '%Y-%m-%d')).month
        # month_today = (datetime.now()).month
        #
        # # Concatenate todo_id and date to create a new identifier
        # id = todo_id + "_" + date
        # query = {'_id': id}
        #
        # # Check if actual data exists
        # l1 = []
        # url = "https://vapt-npcl.myxenius.com/Sensor_newHelper/getDataApi"
        # params = {
        #     'sql': "select raw_data, sensor_id, read_time from dlms_load_profile where sensor_id='{}' and date(read_time)='{}' order by read_time"
        #     .format(todo_id, date),
        #     'type': 'query'
        # }
        # todos_act = requests.get(url, params=params)
        # todos_act.raise_for_status()
        # data = todos_act.json()
        # l1.append(data['resource'])

        # columns = ['sensor', 'Clock', 'R_Voltage', 'Y_Voltage', 'B_Voltage', 'R_Current', 'Y_Current',
        #            'B_Current', 'A', 'BlockEnergy-WhExp', 'B', 'C', 'D', 'BlockEnergy-VAhExp',
        #            'Kwh', 'BlockEnergy-VArhQ1', 'BlockEnergy-VArhQ4', 'BlockEnergy-VAhImp']
        #
        # datalist = [(entry['sensor_id'], entry['raw_data']) for i in range(len(l1)) for entry in l1[i]]
        # df = pd.DataFrame([row[0].split(',') + row[1].split(',') for row in datalist], columns=columns)
        # Access parameters from the query string
        todo_id = request.args.get('id')
        date = request.args.get('date')

        month_from_date = (datetime.strptime(date, '%Y-%m-%d')).month
        month_today = (datetime.now()).month

        # Concatenate todo_id and date to create a new identifier
        id = todo_id + "_" + date
        query = {'_id': id}

        start_date = datetime.strptime(date + " 00:00:00", "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
        end_date = datetime.strptime(date + " 23:59:59", "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")

        act_data = {
            "sensor_id": todo_id,
            "read_time": {"$gte": start_date, "$lt": end_date}
        }
        l1 = []
        # Check if actual data exist
        # for document in documents:
        #     # print()
        #     l1.append(document['resource'])
        # print("helkl")
        # print(l1)

        # url = "https://vapt-npcl.myxenius.com/Sensor_newHelper/getDataApi"
        # params = {
        #     'sql': "select raw_data, sensor_id, read_time from dlms_load_profile where sensor_id='{}' and date(read_time)='{}' order by read_time"
        #     .format(todo_id, date),
        #     'type': 'query'
        # }
        # todos_act = requests.get(url, params=params)
        # todos_act.raise_for_status()
        # data = todos_act.json()
        # l1.append(data['resource'])
        try:
            documents = collection_name4.find(act_data, {"raw_data": 1, "sensor_id": 1, "read_time": 1})
            for document in documents:
                l1.append(document)
        except Exception as e:
            print("Error occurred while fetching documents:", e)

        columns = ['sensor', 'Clock', 'R_Voltage', 'Y_Voltage', 'B_Voltage', 'R_Current', 'Y_Current',
                   'B_Current', 'A', 'BlockEnergy-WhExp', 'B', 'C', 'D', 'BlockEnergy-VAhExp',
                   'Kwh', 'BlockEnergy-VArhQ1', 'BlockEnergy-VArhQ4', 'BlockEnergy-VAhImp']

        # datalist = [(entry['sensor_id'], entry['raw_data']) for i in range(len(l1)) for entry in l1[i]]
        # df = pd.DataFrame([row[0].split(',') + row[1].split(',') for row in datalist], columns=columns)
        datalist = [{'sensor': entry['sensor_id'], **dict(zip(columns[1:], entry['raw_data'].split(',')))} for entry in
                    l1]

        # Create DataFrame using the list of dictionaries and set columns
        df = pd.DataFrame(datalist, columns=columns)

        df = df.drop([
            'R_Voltage', 'Y_Voltage', 'B_Voltage', 'R_Current', 'Y_Current',
            'B_Current', 'A', 'BlockEnergy-WhExp', 'B', 'C', 'D', 'BlockEnergy-VAhExp',
            'BlockEnergy-VArhQ1', 'BlockEnergy-VArhQ4', 'BlockEnergy-VAhImp'], axis=1)
        pd.set_option('display.max_columns', None)
        df['Clock'] = pd.to_datetime(df['Clock'])
        df['Kwh'] = df['Kwh'].astype(float)
        df['Kwh'] = (df['Kwh'] / 1000)
        df.set_index(["Clock"], inplace=True, drop=True)
        df1 = (df[['Kwh']].resample(rule="1H").sum()).round(2)

        percent = 0.0
        act_daily_sum, actual_max_hour, actual_max_value = 0.0, "00", 0.0
        pred_daily_sum, pred_max_hour, pred_max_value = 0.0, "00", 0.0

        # actual data  storing
        formatted_data_act = {"data_act": []}
        if df1.empty is False:
            act_hour_counter = 0
            for value in df1["Kwh"]:
                formatted_data_act["data_act"].append({"clock": str(act_hour_counter).zfill(2), "act_kwh": value})
                act_daily_sum += value
                act_hour_counter += 1
            max_value_dict = max(formatted_data_act['data_act'], key=lambda x: x['act_kwh'])
            actual_max_hour = str(max_value_dict['clock']).zfill(2)
            actual_max_value = round(max_value_dict['act_kwh'], 2)

        if (len(formatted_data_act['data_act'])) < 24:
            for i in range((len(formatted_data_act['data_act'])), 24):
                formatted_data_act["data_act"].append({"clock": str(i).zfill(2), "act_kwh": 0.0})

        actual_data = formatted_data_act

        # Check if predicted data exists
        todos_pred = list(collection_name1.find(query, {'_id': 0, 'data': 1}))
        formatted_data_pred = {"data_pred": []}
        if (len(todos_pred) != 0):
            # Predicted data found, extract values from the data
            pred_hour_counter = 0
            for key, value in todos_pred[0]["data"].items():
                formatted_data_pred["data_pred"].append(
                    {"clock": str(pred_hour_counter).zfill(2), "pre_kwh": round(value["pre_kwh"], 2)})
                pred_daily_sum += (value["pre_kwh"])
                pred_hour_counter += 1

            max_value_dict = max(formatted_data_pred['data_pred'], key=lambda x: x['pre_kwh'])
            pred_max_hour = str(max_value_dict['clock']).zfill(2)
            pred_max_value = round(max_value_dict['pre_kwh'], 2)

        # Predicted data not found or incomplete, create an array of zeros for each hour
        if (len(formatted_data_pred['data_pred'])) < 24:
            for i in range((len(formatted_data_pred['data_pred'])), 24):
                formatted_data_pred["data_pred"].append({"clock": str(i).zfill(2), "pre_kwh": 0.0})

        predicted_data = formatted_data_pred

        if ((month_from_date) != (month_today)) & (act_daily_sum != 0):
            percent = round(abs(((act_daily_sum - pred_daily_sum) / act_daily_sum) * 100), 2)

        # Combine actual and predicted data into a single dictionary
        response_data = {"actual_data": actual_data["data_act"], "predicted_data": predicted_data["data_pred"]}

        return {"rc": 0, "message": "Success",
                "actual_daily_sum": round(act_daily_sum, 2), "pred_daily_sum": round(pred_daily_sum, 2),
                "actual_max_hour": actual_max_hour, "actual_max_value": actual_max_value,
                "pred_max_hour": pred_max_hour, "pred_max_value": pred_max_value,
                "data": response_data,
                "percentage": percent}

    except Exception as e:
        return {"error": str(e)}


@router.route('/getPredDataDaily2', methods=['GET'])
def getPredDataDaily2():
    try:
        # # Access parameters from the query string
        # todo_id = request.args.get('id')
        # date = request.args.get('date')
        #
        # month_from_date = (datetime.strptime(date, '%Y-%m-%d')).month
        # month_today = (datetime.now()).month
        #
        # # Concatenate todo_id and date to create a new identifier
        # id = todo_id + "_" + date
        # query = {'_id': id}
        #
        # # Check if actual data exists
        # l1 = []
        # url = "https://vapt-npcl.myxenius.com/Sensor_newHelper/getDataApi"
        # params = {
        #     'sql': "select raw_data, sensor_id, read_time from dlms_load_profile where sensor_id='{}' and date(read_time)='{}' order by read_time"
        #     .format(todo_id, date),
        #     'type': 'query'
        # }
        # todos_act = requests.get(url, params=params)
        # todos_act.raise_for_status()
        # data = todos_act.json()
        # l1.append(data['resource'])
        #
        # columns = ['sensor', 'Clock', 'R_Voltage', 'Y_Voltage', 'B_Voltage', 'R_Current', 'Y_Current',
        #            'B_Current', 'A', 'BlockEnergy-WhExp', 'B', 'C', 'D', 'BlockEnergy-VAhExp',
        #            'Kwh', 'BlockEnergy-VArhQ1', 'BlockEnergy-VArhQ4', 'BlockEnergy-VAhImp']
        #
        # datalist = [(entry['sensor_id'], entry['raw_data']) for i in range(len(l1)) for entry in l1[i]]
        # df = pd.DataFrame([row[0].split(',') + row[1].split(',') for row in datalist], columns=columns)
        # Access parameters from the query string
        todo_id = request.args.get('id')
        date = request.args.get('date')

        month_from_date = (datetime.strptime(date, '%Y-%m-%d')).month
        month_today = (datetime.now()).month

        # Concatenate todo_id and date to create a new identifier
        id = todo_id + "_" + date
        query = {'_id': id}

        start_date = datetime.strptime(date + " 00:00:00", "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
        end_date = datetime.strptime(date + " 23:59:59", "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")

        act_data = {
            "sensor_id": todo_id,
            "read_time": {"$gte": start_date, "$lt": end_date}
        }
        l1 = []
        # Check if actual data exist
        # for document in documents:
        #     # print()
        #     l1.append(document['resource'])
        # print("helkl")
        # print(l1)

        # url = "https://vapt-npcl.myxenius.com/Sensor_newHelper/getDataApi"
        # params = {
        #     'sql': "select raw_data, sensor_id, read_time from dlms_load_profile where sensor_id='{}' and date(read_time)='{}' order by read_time"
        #     .format(todo_id, date),
        #     'type': 'query'
        # }
        # todos_act = requests.get(url, params=params)
        # todos_act.raise_for_status()
        # data = todos_act.json()
        # l1.append(data['resource'])
        try:
            documents = collection_name4.find(act_data, {"raw_data": 1, "sensor_id": 1, "read_time": 1})
            for document in documents:
                l1.append(document)
        except Exception as e:
            print("Error occurred while fetching documents:", e)

        columns = ['sensor', 'Clock', 'R_Voltage', 'Y_Voltage', 'B_Voltage', 'R_Current', 'Y_Current',
                   'B_Current', 'A', 'BlockEnergy-WhExp', 'B', 'C', 'D', 'BlockEnergy-VAhExp',
                   'Kwh', 'BlockEnergy-VArhQ1', 'BlockEnergy-VArhQ4', 'BlockEnergy-VAhImp']

        # datalist = [(entry['sensor_id'], entry['raw_data']) for i in range(len(l1)) for entry in l1[i]]
        # df = pd.DataFrame([row[0].split(',') + row[1].split(',') for row in datalist], columns=columns)
        datalist = [{'sensor': entry['sensor_id'], **dict(zip(columns[1:], entry['raw_data'].split(',')))} for entry in
                    l1]

        # Create DataFrame using the list of dictionaries and set columns
        df = pd.DataFrame(datalist, columns=columns)

        df = df.drop([
            'R_Voltage', 'Y_Voltage', 'B_Voltage', 'R_Current', 'Y_Current',
            'B_Current', 'A', 'BlockEnergy-WhExp', 'B', 'C', 'D', 'BlockEnergy-VAhExp',
            'BlockEnergy-VArhQ1', 'BlockEnergy-VArhQ4', 'BlockEnergy-VAhImp'], axis=1)
        pd.set_option('display.max_columns', None)
        df['Clock'] = pd.to_datetime(df['Clock'])
        df['Kwh'] = df['Kwh'].astype(float)
        df['Kwh'] = (df['Kwh'] / 1000)
        df.set_index(["Clock"], inplace=True, drop=True)
        df1 = (df[['Kwh']].resample(rule="1H").sum()).round(2)

        percent = 0.0
        act_daily_sum, actual_max_hour, actual_max_value = 0.0, "00", 0.0
        pred_daily_sum, pred_max_hour, pred_max_value = 0.0, "00", 0.0

        # actual data  storing
        formatted_data_act = {"data_act": []}
        if df1.empty is False:
            act_hour_counter = 0
            for value in df1["Kwh"]:
                formatted_data_act["data_act"].append({"clock": str(act_hour_counter).zfill(2), "act_kwh": value})
                act_daily_sum += value
                act_hour_counter += 1
            max_value_dict = max(formatted_data_act['data_act'], key=lambda x: x['act_kwh'])
            actual_max_hour = str(max_value_dict['clock']).zfill(2)
            actual_max_value = round(max_value_dict['act_kwh'], 2)

        if (len(formatted_data_act['data_act'])) < 24:
            for i in range((len(formatted_data_act['data_act'])), 24):
                formatted_data_act["data_act"].append({"clock": str(i).zfill(2), "act_kwh": 0.0})

        actual_data = formatted_data_act

        # Check if predicted data exists
        todos_pred = list(collection_name2.find(query, {'_id': 0, 'data': 1}))
        formatted_data_pred = {"data_pred": []}
        if (len(todos_pred) != 0):
            # Predicted data found, extract values from the data
            pred_hour_counter = 0
            for key, value in todos_pred[0]["data"].items():
                formatted_data_pred["data_pred"].append(
                    {"clock": str(pred_hour_counter).zfill(2), "pre_kwh": round(value["pre_kwh"], 2)})
                pred_daily_sum += (value["pre_kwh"])
                pred_hour_counter += 1

            max_value_dict = max(formatted_data_pred['data_pred'], key=lambda x: x['pre_kwh'])
            pred_max_hour = str(max_value_dict['clock']).zfill(2)
            pred_max_value = round(max_value_dict['pre_kwh'], 2)

        # Predicted data not found or incomplete, create an array of zeros for each hour
        if (len(formatted_data_pred['data_pred'])) < 24:
            for i in range((len(formatted_data_pred['data_pred'])), 24):
                formatted_data_pred["data_pred"].append({"clock": str(i).zfill(2), "pre_kwh": 0.0})

        predicted_data = formatted_data_pred

        if ((month_from_date) != (month_today)) & (act_daily_sum != 0):
            percent = round(abs(((act_daily_sum - pred_daily_sum) / act_daily_sum) * 100), 2)

        # Combine actual and predicted data into a single dictionary
        response_data = {"actual_data": actual_data["data_act"], "predicted_data": predicted_data["data_pred"]}

        return {"rc": 0, "message": "Success",
                "actual_daily_sum": round(act_daily_sum, 2), "pred_daily_sum": round(pred_daily_sum, 2),
                "actual_max_hour": actual_max_hour, "actual_max_value": actual_max_value,
                "pred_max_hour": pred_max_hour, "pred_max_value": pred_max_value,
                "data": response_data,
                "percentage": percent}

    except Exception as e:
        return {"error": str(e)}


@router.route('/getPredDataDaily3', methods=['GET'])
def getPredDataDaily3():
    try:
        # Access parameters from the query string
        # todo_id = request.args.get('id')
        # date = request.args.get('date')
        #
        # month_from_date = (datetime.strptime(date, '%Y-%m-%d')).month
        # month_today = (datetime.now()).month
        #
        # # Concatenate todo_id and date to create a new identifier
        # id = todo_id + "_" + date
        # query = {'_id': id}
        #
        # # Check if actual data exists
        # l1 = []
        # url = "https://vapt-npcl.myxenius.com/Sensor_newHelper/getDataApi"
        # params = {
        #     'sql': "select raw_data, sensor_id, read_time from dlms_load_profile where sensor_id='{}' and date(read_time)='{}' order by read_time"
        #     .format(todo_id, date),
        #     'type': 'query'
        # }
        # todos_act = requests.get(url, params=params)
        # todos_act.raise_for_status()
        # data = todos_act.json()
        # l1.append(data['resource'])
        #
        # columns = ['sensor', 'Clock', 'R_Voltage', 'Y_Voltage', 'B_Voltage', 'R_Current', 'Y_Current',
        #            'B_Current', 'A', 'BlockEnergy-WhExp', 'B', 'C', 'D', 'BlockEnergy-VAhExp',
        #            'Kwh', 'BlockEnergy-VArhQ1', 'BlockEnergy-VArhQ4', 'BlockEnergy-VAhImp']
        #
        # datalist = [(entry['sensor_id'], entry['raw_data']) for i in range(len(l1)) for entry in l1[i]]
        # df = pd.DataFrame([row[0].split(',') + row[1].split(',') for row in datalist], columns=columns)
        # Access parameters from the query string
        todo_id = request.args.get('id')
        date = request.args.get('date')

        month_from_date = (datetime.strptime(date, '%Y-%m-%d')).month
        month_today = (datetime.now()).month

        # Concatenate todo_id and date to create a new identifier
        id = todo_id + "_" + date
        query = {'_id': id}

        start_date = datetime.strptime(date + " 00:00:00", "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
        end_date = datetime.strptime(date + " 23:59:59", "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")

        act_data = {
            "sensor_id": todo_id,
            "read_time": {"$gte": start_date, "$lt": end_date}
        }
        l1 = []
        # Check if actual data exist
        # for document in documents:
        #     # print()
        #     l1.append(document['resource'])
        # print("helkl")
        # print(l1)

        # url = "https://vapt-npcl.myxenius.com/Sensor_newHelper/getDataApi"
        # params = {
        #     'sql': "select raw_data, sensor_id, read_time from dlms_load_profile where sensor_id='{}' and date(read_time)='{}' order by read_time"
        #     .format(todo_id, date),
        #     'type': 'query'
        # }
        # todos_act = requests.get(url, params=params)
        # todos_act.raise_for_status()
        # data = todos_act.json()
        # l1.append(data['resource'])
        try:
            documents = collection_name4.find(act_data, {"raw_data": 1, "sensor_id": 1, "read_time": 1})
            for document in documents:
                l1.append(document)
        except Exception as e:
            print("Error occurred while fetching documents:", e)

        columns = ['sensor', 'Clock', 'R_Voltage', 'Y_Voltage', 'B_Voltage', 'R_Current', 'Y_Current',
                   'B_Current', 'A', 'BlockEnergy-WhExp', 'B', 'C', 'D', 'BlockEnergy-VAhExp',
                   'Kwh', 'BlockEnergy-VArhQ1', 'BlockEnergy-VArhQ4', 'BlockEnergy-VAhImp']

        # datalist = [(entry['sensor_id'], entry['raw_data']) for i in range(len(l1)) for entry in l1[i]]
        # df = pd.DataFrame([row[0].split(',') + row[1].split(',') for row in datalist], columns=columns)
        datalist = [{'sensor': entry['sensor_id'], **dict(zip(columns[1:], entry['raw_data'].split(',')))} for entry in
                    l1]

        # Create DataFrame using the list of dictionaries and set columns
        df = pd.DataFrame(datalist, columns=columns)

        df = df.drop([
            'R_Voltage', 'Y_Voltage', 'B_Voltage', 'R_Current', 'Y_Current',
            'B_Current', 'A', 'BlockEnergy-WhExp', 'B', 'C', 'D', 'BlockEnergy-VAhExp',
            'BlockEnergy-VArhQ1', 'BlockEnergy-VArhQ4', 'BlockEnergy-VAhImp'], axis=1)
        pd.set_option('display.max_columns', None)
        df['Clock'] = pd.to_datetime(df['Clock'])
        df['Kwh'] = df['Kwh'].astype(float)
        df['Kwh'] = (df['Kwh'] / 1000)
        df.set_index(["Clock"], inplace=True, drop=True)
        df1 = (df[['Kwh']].resample(rule="1H").sum()).round(2)

        percent = 0.0
        act_daily_sum, actual_max_hour, actual_max_value = 0.0, "00", 0.0
        pred_daily_sum, pred_max_hour, pred_max_value = 0.0, "00", 0.0

        # actual data  storing
        formatted_data_act = {"data_act": []}
        if df1.empty is False:
            act_hour_counter = 0
            for value in df1["Kwh"]:
                formatted_data_act["data_act"].append({"clock": str(act_hour_counter).zfill(2), "act_kwh": value})
                act_daily_sum += value
                act_hour_counter += 1
            max_value_dict = max(formatted_data_act['data_act'], key=lambda x: x['act_kwh'])
            actual_max_hour = str(max_value_dict['clock']).zfill(2)
            actual_max_value = round(max_value_dict['act_kwh'], 2)

        if (len(formatted_data_act['data_act'])) < 24:
            for i in range((len(formatted_data_act['data_act'])), 24):
                formatted_data_act["data_act"].append({"clock": str(i).zfill(2), "act_kwh": 0.0})

        actual_data = formatted_data_act

        # Check if predicted data exists
        todos_pred = list(collection_name3.find(query, {'_id': 0, 'data': 1}))
        formatted_data_pred = {"data_pred": []}
        if (len(todos_pred) != 0):
            # Predicted data found, extract values from the data
            pred_hour_counter = 0
            for key, value in todos_pred[0]["data"].items():
                formatted_data_pred["data_pred"].append(
                    {"clock": str(pred_hour_counter).zfill(2), "pre_kwh": round(value["pre_kwh"], 2)})
                pred_daily_sum += (value["pre_kwh"])
                pred_hour_counter += 1

            max_value_dict = max(formatted_data_pred['data_pred'], key=lambda x: x['pre_kwh'])
            pred_max_hour = str(max_value_dict['clock']).zfill(2)
            pred_max_value = round(max_value_dict['pre_kwh'], 2)

        # Predicted data not found or incomplete, create an array of zeros for each hour
        if (len(formatted_data_pred['data_pred'])) < 24:
            for i in range((len(formatted_data_pred['data_pred'])), 24):
                formatted_data_pred["data_pred"].append({"clock": str(i).zfill(2), "pre_kwh": 0.0})

        predicted_data = formatted_data_pred

        if ((month_from_date) != (month_today)) & (act_daily_sum != 0):
            percent = round(abs(((act_daily_sum - pred_daily_sum) / act_daily_sum) * 100), 2)

        # Combine actual and predicted data into a single dictionary
        response_data = {"actual_data": actual_data["data_act"], "predicted_data": predicted_data["data_pred"]}

        return {"rc": 0, "message": "Success",
                "actual_daily_sum": round(act_daily_sum, 2), "pred_daily_sum": round(pred_daily_sum, 2),
                "actual_max_hour": actual_max_hour, "actual_max_value": actual_max_value,
                "pred_max_hour": pred_max_hour, "pred_max_value": pred_max_value,
                "data": response_data,
                "percentage": percent}

    except Exception as e:
        return {"error": str(e)}

@router.route('/getPredDataMonthlyjdvvnl', methods=['POST'])
def getPredDataMonthlyjdvvnl():
    try:
        # todo_id = request.args.get('id')
        # date = request.args.get('date')
        data = request.get_json()
        todo_id = data.get('id')
        date = data.get('date')

        month = datetime.strptime(date, '%Y-%m').month
        year = datetime.strptime(date, '%Y-%m').year
        day = monthrange(year, month)
        last_day = day[1]

        start_date = datetime(year, month, 1).strftime("%Y-%m-%d")
        end_date = datetime(year, month, last_day).strftime("%Y-%m-%d")


        act_data = {
            "parent_sensor_id": todo_id,
            "meter_date": {"$gte": start_date, "$lte": end_date}
        }
        formatted_month = '{:02d}'.format(month)
        formatted_year = '{:04d}'.format(year)

        # Convert the formatted month and year to strings
        month = str(formatted_month)
        year = str(formatted_year)
        pred_data = {
            "sensor_id": todo_id,
            "month": month,
            "year" : year
        }

        l1 = []
        try:
            documents = collection_name5.find(act_data, {"meter_date": 1, "consumed_KWh": 1})
            for document in documents:
                l1.append(document)
        except Exception as e:
            print("Error occurred while fetching documents:", e)

        columns = ['meter_date', 'consumed_KWh']
        datalist = [(entry['meter_date'], entry['consumed_KWh']) for entry in l1]
        # print(datalist)
        # return

        df1 = pd.DataFrame(datalist, columns=columns)
        # print(df1.info())

        df1['meter_date'] = pd.to_datetime(df1['meter_date'])
        df1['consumed_KWh'] = df1['consumed_KWh'].astype(float)
        # df1['load'] = round(df1['consumed_KWh'].astype(float)/24)
        df1.set_index(["meter_date"], inplace=True)

        # df1 = df.resample(rule="1D").sum().round(2)
        # print(df1)

        percent = 0.0
        act_monthly_sum, act_max_date, act_max_date_value = 0.0, f"{year}-{str(month).zfill(2)}-01", 0.0
        pred_monthly_sum, pred_max_date, pred_max_date_value = 0.0, f"{year}-{str(month).zfill(2)}-{last_day}", 0.0

        formatted_data_act = {"data_act": []}
        first_day = 1
        if not df1.empty:
            # Actual data found, extract values from the data
            for index, row in df1.iterrows():
                formatted_data_act["data_act"].append(
                    {"clock": f"{index.date()}", "act_kwh": row['consumed_KWh'], "act_load": round(row['consumed_KWh']/24, 2)})
                act_monthly_sum += row['consumed_KWh']
                first_day += 1

            max_value_dict = max(formatted_data_act['data_act'], key=lambda x: x['act_kwh'])
            act_max_date = max_value_dict['clock']
            act_max_date_value = max_value_dict['act_kwh']

        if len(formatted_data_act['data_act']) != last_day:
            for _ in range(len(formatted_data_act['data_act']) + 1, last_day + 1):
                formatted_data_act["data_act"].append(
                    {"clock": f"{year}-{str(month).zfill(2)}-{str(first_day).zfill(2)}", "act_kwh": 0.0})
                first_day += 1

        actual_data = formatted_data_act

        # Check if predicted data exists
        todos_pred = list(collection_name6.find(pred_data, {'_id': 1, 'data': 1}))

        print(todos_pred)
        formatted_data_pred = {"data_pred": []}
        if todos_pred:
            # Predicted data found, extract values from the data
            for i in range(len(todos_pred)):
                b = todos_pred[i]['_id'].split("_")
                date2 = b[1]
                pred_daily_sum = sum(
                    todos_pred[i]['data'][str(day)]['pre_kwh'] for day in range(len(todos_pred[i]['data'])))
                formatted_data_pred["data_pred"].append({"clock": date2, "pre_kwh": round(pred_daily_sum, 2), "pre_load": round(pred_daily_sum/24, 2)})

                pred_monthly_sum += pred_daily_sum

            max_value_dict = max(formatted_data_pred['data_pred'], key=lambda x: x['pre_kwh'])
            pred_max_date = max_value_dict['clock']
            pred_max_date_value = max_value_dict['pre_kwh']

        # Predicted data not found, create an array of zeros for each hour
        if len(todos_pred) != last_day:
            for _ in range(len(todos_pred) + 1, last_day + 1):
                formatted_data_pred['data_pred'].append(
                    {"clock": f"{year}-{str(month).zfill(2)}-{str(_).zfill(2)}", "pre_kwh": 0.0})

        predicted_data = formatted_data_pred

        # if month != datetime.now().month and act_monthly_sum != 0.0:
        #     percent = round(abs((act_monthly_sum - pred_monthly_sum) / act_monthly_sum) * 100, 2)

        # Combine actual and predicted data into a single dictionary
        response_data = {"actual_data": actual_data["data_act"], "predicted_data": predicted_data["data_pred"]}
        return {"rc": 0, "message": "Success", "sensor_id": todo_id, "actual_load": round(act_monthly_sum/24, 2),"pred_load": round(pred_monthly_sum/24, 2),
                "act_max_date_value": act_max_date_value, "act_max_date": act_max_date,
                "pred_max_date_value": pred_max_date_value, "pred_max_date": pred_max_date,
                "act_monthly_sum": round(act_monthly_sum, 2), "pred_monthly_sum": round(pred_monthly_sum, 2),
                 "data": response_data}

    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}

@router.route('/getJDVVNLDailyData', methods=['POST'])
def getJDVVNLDailyData():
    try:
        # todo_id = request.args.get('id')
        # date = request.args.get('date')
        data = request.get_json()
        todo_id = data.get('id')
        date = data.get('date')
        
        prev_start_date = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=1)).replace(hour=23, minute=45, second=0)
        start_date = prev_start_date.strftime("%Y-%m-%d %H:%M:%S")
        end_date = datetime.strptime(date + " 23:59:59", "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")

        percent = 0.0
        act_daily_sum, actual_max_hour, actual_max_value = 0, "0000-00-00 00:00:00", 0
        pred_daily_sum, pred_max_hour, pred_max_value = 0, "0000-00-00 00:00:00", 0
        response_data = {}
        # Check if actual data exist        
        mongo_query = {
            'sensor_id': todo_id,
            "creation_time": {"$gte": start_date, "$lt": end_date}}
        try:
            document = list(collection_name5.find(mongo_query,{"_id": 0,"creation_time": 1, "opening_KWh": 1}))
            if len(document)!= 0:
                act_df = pd.DataFrame(document)
                act_df['creation_time'] = pd.to_datetime(act_df['creation_time'])
                act_df.set_index('creation_time', inplace=True, drop=True)
                act_df.sort_index(inplace=True)
                act_df.loc[act_df['opening_KWh']==0,"opening_KWh"] = np.nan
                act_df.loc[act_df['opening_KWh'].first_valid_index():]
                act_df.bfill(inplace=True)

                resampled_act_df = act_df.resample(rule="15min").asfreq() 
                resampled_act_df.interpolate(method="linear", inplace=True)
                resampled_act_df['prev_opening'] = resampled_act_df['opening_KWh'].shift(1)
                resampled_act_df.dropna(inplace=True)
                resampled_act_df['consumed_unit'] = (resampled_act_df['opening_KWh'] - resampled_act_df['prev_opening']).round(2)
                resampled_act_df.loc[resampled_act_df['consumed_unit'] < 0, "opening_KWh"] = resampled_act_df["prev_opening"]
                resampled_act_df.loc[resampled_act_df['consumed_unit'] < 0, "consumed_unit"] = 0

            else:
                print("no actual data available for that day")

            new_act_df = pd.DataFrame({"consumed_unit":[0]},index = pd.date_range(date, end_date, freq="15min"))
            if len(document)!= 0:
                new_act_df.update(resampled_act_df)

            actual_max_value = new_act_df['consumed_unit'].max()
            index_with_max_consumed_unit = new_act_df[new_act_df['consumed_unit']==actual_max_value].index
            actual_max_hour = index_with_max_consumed_unit[0].strftime("%Y-%m-%d %H:%M:%S")   
            act_daily_sum = new_act_df['consumed_unit'].sum()

            new_act_df.reset_index(inplace=True)
            act_data_dict = new_act_df.to_dict()

            formatted_data_act = {"data_act": []}
            for i in range(len(new_act_df)):
                formatted_data_act["data_act"].append({"clock":act_data_dict['index'][i].strftime("%H:%M:%S"), "consumed_unit":float(act_data_dict['consumed_unit'][i])})
            response_data['actual_data'] = formatted_data_act['data_act']
        except Exception as e:
            print("Error occurred while fetching actual data:", e)

        # Check if predicted data exists
        pred_data_date = (datetime.strptime(date, "%Y-%m-%d"))
        mongo_query = {
            'sensor_id': todo_id,
            "day":str(pred_data_date.day).zfill(2),
            "month":str(pred_data_date.month).zfill(2),
            "year": str(pred_data_date.year)}
        try:
            pred_document = []
            pred_document = list(collection_name7.find(mongo_query,{"_id" : 0,"data" : 1}))
            if len(pred_document)!= 0:
                pred_df = pd.DataFrame(pred_document[0]['data']).transpose()
                pred_df.rename(columns={'pre_kwh':'consumed_unit'}, inplace=True)
                pred_df.index = pd.date_range(date, periods= len(pred_df), freq="15min")

            else:
                print("no prediction data available for that day")
            new_pred_df = pd.DataFrame({"consumed_unit":[0]},index = pd.date_range(date, end_date, freq="15min"))

            if len(pred_document)!= 0:
                new_pred_df.update(pred_df)
            pred_max_value = new_pred_df['consumed_unit'].max()
            index_with_max_consumed_unit_pred = new_pred_df[new_pred_df['consumed_unit']==pred_max_value].index
            pred_max_hour = index_with_max_consumed_unit_pred[0].strftime("%Y-%m-%d %H:%M:%S")   
            pred_daily_sum = new_pred_df['consumed_unit'].sum()

            new_pred_df.reset_index(inplace=True)
            pred_data_dict = new_pred_df.to_dict()

            formatted_data_pred = {"data_pred": []}
            for j in range(len(new_pred_df)):
                formatted_data_pred["data_pred"].append({"clock":pred_data_dict['index'][j].strftime("%H:%M:%S"), "consumed_unit":float(pred_data_dict['consumed_unit'][j])})

            response_data['predicted_data'] = formatted_data_pred['data_pred']
        except Exception as e:
            print("Error occurred while fetching predicion data:", e)
        
        return {"rc": 0, "message": "Success",
                "actual_max_hour": str(actual_max_hour),
                "actual_max_value": round(float(actual_max_value),2),
                "actual_daily_sum": round(float(act_daily_sum),2),
                "pred_daily_sum": round(float(pred_daily_sum), 2),
                "pred_max_hour": str(pred_max_hour),
                "pred_max_value": round(float(pred_max_value),2),
                "data": response_data,
                # "percentage": percent
                }

    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}


@router.route('/get_jdvvnlSensorList', methods=['POST'])
def get_jdvvnlSensorList():
    try:
        data = request.get_json()
        circle_id = data.get('circle_id')
        # circle_id = 'd07d36a0-facd-11ed-a890-0242bed38519'
        data = list(collection_name8.find({'circle_id':circle_id,"type":"AC_METER","admin_status": {"$in": ['N', 'S', 'U']}},{"_id":0,"id":1,"UOM": 1,"name":1,"asset_id":1}))
        return jsonify({"rc": 0, "message": "Success", 'sensorList': data})

    except Exception as e:
        print(e)
        return jsonify({"rc": -1, "message": "error"}), 500


@router.route('/get_jdvvnlcircleList', methods=['POST'])
def get_jdvvnlcircleList():
    try:
        distinct_circle_id = {"cf65ac20-facd-11ed-a890-0242bed38519":    'JODHPUR CITY',
                                'd042ecc0-facd-11ed-a890-0242bed38519' :   'PALI',
                                'd077df70-facd-11ed-a890-0242bed38519' :   "JODHPUR DC",
                                'd07d36a0-facd-11ed-a890-0242bed38519'  :  "JAISALMER",
                                'd08b1950-facd-11ed-a890-0242bed38519'  :  "SRI GANGANAGAR",
                                'd0d93950-facd-11ed-a890-0242bed38519' :   "BARMER",
                                'd0f23f90-facd-11ed-a890-0242bed38519' :   "SIROHI",
                                'd11ef4e0-facd-11ed-a890-0242bed38519' :   "JALORE",
                                'd1331920-facd-11ed-a890-0242bed38519' :   "HANUMANGARH",
                                'd1489cf0-facd-11ed-a890-0242bed38519'  :  "BIKANER",
                                'e5533a70-facd-11ed-a890-0242bed38519'  :  "CHURU"}
        # distinct_circle_id = collection_name8.distinct("circle_id", {"utility": "2", "type": "AC_METER", "admin_status": {"$in": ['N', 'S', 'U']}})
        return jsonify({"rc": 0, "message": "Success", 'circleList': distinct_circle_id})

    except Exception as e:
        print(e)
        return jsonify({"rc": -1, "message": "error"}), 500

