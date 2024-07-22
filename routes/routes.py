import concurrent
from calendar import monthrange
from concurrent.futures import ThreadPoolExecutor

from flask import Blueprint, request, jsonify

from config.db import collection_name, collection_name1, collection_name2, collection_name3, collection_name4, \
    collection_name5, collection_name6, collection_name7, collection_name8, collection_name9, collection_name10, collection_name13

router = Blueprint('router', __name__)
import requests
import pandas as pd
from datetime import datetime, timedelta
import traceback
import numpy as np
from logs import logs_config


@router.route('/get_sensorListV1', methods=['GET'])
def get_sensorListV1():
    try:
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


@router.route('/getPredDataDailyV1', methods=['GET'])
def getPredDataDailyV1():
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
            "year": year
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
                    {"clock": f"{index.date()}", "act_kwh": row['consumed_KWh'],
                     "act_load": round(row['consumed_KWh'] / 24, 2)})
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
                formatted_data_pred["data_pred"].append(
                    {"clock": date2, "pre_kwh": round(pred_daily_sum, 2), "pre_load": round(pred_daily_sum / 24, 2)})

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
        return {"rc": 0, "message": "Success", "sensor_id": todo_id, "actual_load": round(act_monthly_sum / 24, 2),
                "pred_load": round(pred_monthly_sum / 24, 2),
                "act_max_date_value": act_max_date_value, "act_max_date": act_max_date,
                "pred_max_date_value": pred_max_date_value, "pred_max_date": pred_max_date,
                "act_monthly_sum": round(act_monthly_sum, 2), "pred_monthly_sum": round(pred_monthly_sum, 2),
                "data": response_data}

    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}


@router.route('/getweatherdata', methods=['POST'])
def getweatherdata():
    try:
        lst = ['667572f85ded75.67576759',
               '667997aaa85681.59292546',
               '667cf45531cb64.78079103',
               '667d76057bd676.87408467',
               '667d76830d35c0.44956320',
               '667ef64f388065.50412235',
               '667ef71343e491.54578071',
               '667ef806470426.32625353',
               '667f00182639e6.29627216',
               '667f00322b6e24.78981311',
               '667f0071e87539.72424501',
               '6680dafb98c536.71089464',
               '6680e0b51934d8.15669586',
               '6680e3a8345f51.33991924',
               '6680e47b643896.02283028',
               '66839cedc7aec1.26001694'
               ]

        pipeline = [
            {"$match": {'type': 'AC', 'admin_status': {"$in": ['N', 'S', 'U']},
                        'site_id': {"$in": lst}}},
            {"$group": {
                "_id": "$site_id",
                "latitude": {"$min": "$latitude"},
                "longitude": {"$min": "$longitude"},
                "sensors": {
                    "$addToSet": {"id": "$id", "name": "$name", "latitude": "$latitude", "longitude": "$longitude"}}
            }}
        ]

        # Execute the pipeline and retrieve the result
        result = list(collection_name7.aggregate(pipeline))
        print(result)

        # Construct data to be inserted into MongoDB
        bulk_insert_data = []

        # Iterate over each site
        for site_data in result:
            url = f"https://archive-api.open-meteo.com/v1/archive?latitude={site_data['latitude']}&longitude={site_data['longitude']}&start_date=2024-06-21&end_date=2024-07-15&hourly=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,wind_speed_10m,wind_speed_100m"
            print(url)
            response = requests.get(url)
            response.raise_for_status()
            weather_data = response.json()

            # Process weather data if available
            if "hourly" in weather_data:
                for i in range(len(weather_data['hourly']['time'])):
                    hour_data = {
                        "_id": f"{site_data['_id']}_{weather_data['hourly']['time'][i]}",  # MongoDB's unique identifier
                        "site_id": site_data["_id"],
                        "time": weather_data['hourly']['time'][i],
                        "temperature_2m": weather_data['hourly'].get('temperature_2m', [])[i],
                        "relative_humidity_2m": weather_data['hourly'].get('relative_humidity_2m', [])[i],
                        "apparent_temperature": weather_data['hourly'].get('apparent_temperature', [])[i],
                        "precipitation": weather_data['hourly'].get('precipitation', [])[i],
                        "wind_speed_10m": weather_data['hourly'].get('wind_speed_10m', [])[i],
                        "wind_speed_100m": weather_data['hourly'].get('wind_speed_100m', [])[i],
                        "creation_time_iso": datetime.utcfromtimestamp(
                            datetime.strptime(weather_data['hourly']['time'][i],
                                              '%Y-%m-%dT%H:%M').timestamp()).isoformat()
                    }

                    bulk_insert_data.append(hour_data)
                    # print(bulk_insert_data)

        # Insert the data into MongoDB in bulk
        if bulk_insert_data:
            collection_name8.insert_many(bulk_insert_data)
            return {"message": "Weather data fetched and stored successfully"}
        else:
            return {"message": "No weather data available for the specified sites"}

    except Exception as e:
        return {"error": str(e)}


# weather data forcasted
@router.route('/getweatherdataF', methods=['POST'])
def getweatherdataF():
    try:
        lst = ['667572f85ded75.67576759',
               '667997aaa85681.59292546',
               '667cf45531cb64.78079103',
               '667d76057bd676.87408467',
               '667d76830d35c0.44956320',
               '667ef64f388065.50412235',
               '667ef71343e491.54578071',
               '667ef806470426.32625353',
               '667f00182639e6.29627216',
               '667f00322b6e24.78981311',
               '667f0071e87539.72424501',
               '6680dafb98c536.71089464',
               '6680e0b51934d8.15669586',
               '6680e3a8345f51.33991924',
               '6680e47b643896.02283028',
               '66839cedc7aec1.26001694'
               ]

        pipeline = [
            {"$match": {'type': 'AC', 'admin_status': {"$in": ['N', 'S', 'U']},
                        'site_id': {"$in": lst}}},
            {"$group": {
                "_id": "$site_id",
                "latitude": {"$min": "$latitude"},
                "longitude": {"$min": "$longitude"},
                "sensors": {
                    "$addToSet": {"id": "$id", "name": "$name", "latitude": "$latitude", "longitude": "$longitude"}}
            }}
        ]
        print(pipeline)

        # Execute the pipeline and retrieve the result
        result = list(collection_name7.aggregate(pipeline))
        print(result)

        # Construct data to be inserted into MongoDB
        bulk_insert_data = []

        # Iterate over each site
        for site_data in result:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={site_data['latitude']}&longitude={site_data['longitude']}&hourly=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,wind_speed_10m,wind_speed_80m&start_date=2024-07-16&end_date=2024-08-02"
            print(url)
            response = requests.get(url)
            response.raise_for_status()
            weather_data = response.json()

            # Process weather data if available
            if "hourly" in weather_data:
                for i in range(len(weather_data['hourly']['time'])):
                    hour_data = {
                        "_id": f"{site_data['_id']}_{weather_data['hourly']['time'][i]}",  # MongoDB's unique identifier
                        "site_id": site_data["_id"],
                        "time": weather_data['hourly']['time'][i],
                        "temperature_2m": weather_data['hourly'].get('temperature_2m', [])[i],
                        "relative_humidity_2m": weather_data['hourly'].get('relative_humidity_2m', [])[i],
                        "apparent_temperature": weather_data['hourly'].get('apparent_temperature', [])[i],
                        "precipitation": weather_data['hourly'].get('precipitation', [])[i],
                        "wind_speed_10m": weather_data['hourly'].get('wind_speed_10m', [])[i],
                        "wind_speed_100m": weather_data['hourly'].get('wind_speed_80m', [])[i],
                        "creation_time_iso": datetime.utcfromtimestamp(
                            datetime.strptime(weather_data['hourly']['time'][i],
                                              '%Y-%m-%dT%H:%M').timestamp()).isoformat()
                    }

                    bulk_insert_data.append(hour_data)
                    # print(bulk_insert_data)

        # Insert the data into MongoDB in bulk
        if bulk_insert_data:
            collection_name8.insert_many(bulk_insert_data)
            return {"message": "Weather data fetched and stored successfully"}
        else:
            return {"message": "No weather data available for the specified sites"}

    except Exception as e:
        return {"error": str(e)}


@router.route('/getJDVVNLDailyData', methods=['POST'])
def getJDVVNLDailyData():
    try:
        # todo_id = request.args.get('id')
        # date = request.args.get('date')
        data = request.get_json()
        todo_id = data.get('id')
        date = data.get('date')

        prev_start_date = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=1)).replace(hour=23, minute=45,
                                                                                            second=0)
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
            document = list(collection_name5.find(mongo_query, {"_id": 0, "creation_time": 1, "opening_KWh": 1}))
            if len(document) != 0:
                act_df = pd.DataFrame(document)
                act_df['creation_time'] = pd.to_datetime(act_df['creation_time'])
                act_df.set_index('creation_time', inplace=True, drop=True)
                act_df.sort_index(inplace=True)
                act_df.loc[act_df['opening_KWh'] == 0, "opening_KWh"] = np.nan
                act_df.loc[act_df['opening_KWh'].first_valid_index():]
                act_df.bfill(inplace=True)

                resampled_act_df = act_df.resample(rule="15min").asfreq()
                resampled_act_df.interpolate(method="linear", inplace=True)
                resampled_act_df['prev_opening'] = resampled_act_df['opening_KWh'].shift(1)
                resampled_act_df.dropna(inplace=True)
                resampled_act_df['consumed_unit'] = (
                        resampled_act_df['opening_KWh'] - resampled_act_df['prev_opening']).round(2)
                resampled_act_df.loc[resampled_act_df['consumed_unit'] < 0, "opening_KWh"] = resampled_act_df[
                    "prev_opening"]
                resampled_act_df.loc[resampled_act_df['consumed_unit'] < 0, "consumed_unit"] = 0

            else:
                print("no actual data available for that day")

            new_act_df = pd.DataFrame({"consumed_unit": [0]}, index=pd.date_range(date, end_date, freq="15min"))
            if len(document) != 0:
                new_act_df.update(resampled_act_df)

            actual_max_value = new_act_df['consumed_unit'].max()
            index_with_max_consumed_unit = new_act_df[new_act_df['consumed_unit'] == actual_max_value].index
            actual_max_hour = index_with_max_consumed_unit[0].strftime("%Y-%m-%d %H:%M:%S")
            act_daily_sum = new_act_df['consumed_unit'].sum()

            new_act_df.reset_index(inplace=True)
            act_data_dict = new_act_df.to_dict()

            formatted_data_act = {"data_act": []}
            for i in range(len(new_act_df)):
                formatted_data_act["data_act"].append({"clock": act_data_dict['index'][i].strftime("%H:%M:%S"),
                                                       "consumed_unit": float(act_data_dict['consumed_unit'][i])})
            response_data['actual_data'] = formatted_data_act['data_act']
        except Exception as e:
            print("Error occurred while fetching actual data:", e)

        # Check if predicted data exists
        pred_data_date = (datetime.strptime(date, "%Y-%m-%d"))
        mongo_query = {
            'sensor_id': todo_id,
            "day": str(pred_data_date.day).zfill(2),
            "month": str(pred_data_date.month).zfill(2),
            "year": str(pred_data_date.year)}
        try:
            pred_document = []
            pred_document = list(collection_name9.find(mongo_query, {"_id": 0, "data": 1}))
            if len(pred_document) != 0:
                pred_df = pd.DataFrame(pred_document[0]['data']).transpose()
                pred_df.rename(columns={'pre_kwh': 'consumed_unit'}, inplace=True)
                pred_df.index = pd.date_range(date, periods=len(pred_df), freq="15min")

            else:
                print("no prediction data available for that day")
            new_pred_df = pd.DataFrame({"consumed_unit": [0]}, index=pd.date_range(date, end_date, freq="15min"))

            if len(pred_document) != 0:
                new_pred_df.update(pred_df)
            pred_max_value = new_pred_df['consumed_unit'].max()
            index_with_max_consumed_unit_pred = new_pred_df[new_pred_df['consumed_unit'] == pred_max_value].index
            pred_max_hour = index_with_max_consumed_unit_pred[0].strftime("%Y-%m-%d %H:%M:%S")
            pred_daily_sum = new_pred_df['consumed_unit'].sum()

            new_pred_df.reset_index(inplace=True)
            pred_data_dict = new_pred_df.to_dict()

            formatted_data_pred = {"data_pred": []}
            for j in range(len(new_pred_df)):
                formatted_data_pred["data_pred"].append({"clock": pred_data_dict['index'][j].strftime("%H:%M:%S"),
                                                         "consumed_unit": float(pred_data_dict['consumed_unit'][j])})

            response_data['predicted_data'] = formatted_data_pred['data_pred']
        except Exception as e:
            print("Error occurred while fetching predicion data:", e)

        return {"rc": 0, "message": "Success",
                "actual_max_hour": str(actual_max_hour),
                "actual_max_value": round(float(actual_max_value), 2),
                "actual_daily_sum": round(float(act_daily_sum), 2),
                "pred_daily_sum": round(float(pred_daily_sum), 2),
                "pred_max_hour": str(pred_max_hour),
                "pred_max_value": round(float(pred_max_value), 2),
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
        data = list(collection_name7.find(
            {'circle_id': circle_id, "type": "AC_METER", "admin_status": {"$in": ['N', 'S', 'U']}},
            {"_id": 0, "id": 1, "UOM": 1, "name": 1, "asset_id": 1}))
        return jsonify({"rc": 0, "message": "Success", 'sensorList': data})

    except Exception as e:
        print(e)
        return jsonify({"rc": -1, "message": "error"}), 500


@router.route('/get_jdvvnlcircleList', methods=['POST'])
def get_jdvvnlcircleList():
    try:
        distinct_circle_id = {"cf65ac20-facd-11ed-a890-0242bed38519": 'JODHPUR CITY',
                              'd042ecc0-facd-11ed-a890-0242bed38519': 'PALI',
                              'd077df70-facd-11ed-a890-0242bed38519': "JODHPUR DC",
                              'd07d36a0-facd-11ed-a890-0242bed38519': "JAISALMER",
                              'd08b1950-facd-11ed-a890-0242bed38519': "SRI GANGANAGAR",
                              'd0d93950-facd-11ed-a890-0242bed38519': "BARMER",
                              'd0f23f90-facd-11ed-a890-0242bed38519': "SIROHI",
                              'd11ef4e0-facd-11ed-a890-0242bed38519': "JALORE",
                              'd1331920-facd-11ed-a890-0242bed38519': "HANUMANGARH",
                              'd1489cf0-facd-11ed-a890-0242bed38519': "BIKANER",
                              'e5533a70-facd-11ed-a890-0242bed38519': "CHURU"}
        # distinct_circle_id = collection_name8.distinct("circle_id", {"utility": "2", "type": "AC_METER", "admin_status": {"$in": ['N', 'S', 'U']}})
        return jsonify({"rc": 0, "message": "Success", 'circleList': distinct_circle_id})

    except Exception as e:
        print(e)
        return jsonify({"rc": -1, "message": "error"}), 500


@router.route('/circle_id', methods=['POST'])
def circle_id():
    try:
        data = collection_name10.find({}, {"_id": 0, "id": 1}, )
        result = list(data)
        for doc in result:
            if '_id' in doc:
                doc['_id'] = str(doc['_id'])
        logs_config.logger.info("Fetched circle IDs from database")
        return result
    except Exception as e:
        logs_config.logger.error("Error fetching circle IDs:", exc_info=True)
        raise e


@router.route('/sensor_ids', methods=['POST'])
def sensor_ids(circle_id):
    # circle_id = request.args.get("circle_id")

    try:
        query = {
            "circle_id": circle_id,
            "type": "AC_METER",
            "admin_status": {"$in": ["N", "S", "U"]},
            "utility": "2"
        }
        projection = {"id": 1, "_id": 0}
        sensor_id = collection_name7.find(query, projection)
        return [doc["id"] for doc in sensor_id]

    except Exception as e:
        logs_config.logger.error("Error fetching sensor IDs:", exc_info=True)
        raise e


def data_fetch(sensor_id, site_id, conn):
    try:
        fromId = sensor_id + "-2024-01-01 00:00:00"
        toId = sensor_id + "-2024-03-31 23:59:59"
        query = {"_id": {"$gte": fromId, "$lt": toId}}
        results = list(conn.load_profile_jdvvnl.find(query))

        if results:
            for doc in results:
                # Convert '_id' to string for JSON compatibility
                doc['_id'] = str(doc['_id'])
        # transformed_data = dataTransformation.init_transformation(results, site_id)
        logs_config.logger.info(f"Fetched {len(results)} documents for sensor_id: {sensor_id}")
        return results
    except Exception as e:
        logs_config.logger.error(f"Error fetching data for sensor_id {sensor_id}:", exc_info=True)
        return []


@router.route('/fetch_data_for_sensors', methods=['POST'])
def fetch_data_for_sensors():
    circle_id = request.args.get("circle_id")
    conn = request.args.get("conn")
    sensor_info = sensor_ids(circle_id)
    sensors_id = [doc["id"] for doc in sensor_info]
    sites = [doc["site_id"] for doc in sensor_info]
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(data_fetch, sensor_id, site_id, conn): (sensor_id, site_id) for sensor_id, site_id in
                   zip(sensors_id, sites)}

    results = []
    for future in concurrent.futures.as_completed(futures):
        sensor_id = futures[future]
        try:
            results.append(future.result())
        except Exception as exc:
            logs_config.logger.error(f"Error fetching data for sensor_id {sensor_id}: {exc}")

    return jsonify(results)

'''========================================================JPDCL API======================================================================'''
@router.route('/get_sensorList', methods=['GET'])
def get_sensorList():
    sensor_ids = ['66755ea75d9656.09451425',
               '66792887ab2bf0.01972524',
               '66798b07a176f7.28421426',
               '66796b38011256.43379844',
               '66796c7d38ef95.94782159',
               '667975ae47a9d3.45611637',
               '66798c998af0a4.39772704',
               '66798d6f3b99a8.11022930',
               '66798dd85a2067.34235472',
               '66798e4245c0d7.47939284',
               '667bd42c040dd4.71905290',
               '667be335c9c907.26863078',
               '66798f9a010539.13786166',
               '66798d04b74f65.00513254',
               '667be7240c74a4.64013414',
               '66798f359b8a34.89774241',
               '66799027e46756.51131984',
               '667be8df45fab9.64137172',
               '667be9cb3031e1.24562866',
               '667989e30478b9.04540881',
               '667beac5d62785.79876238',
               '667c0ece2d5d57.23218009',
               '667be57d43ddc1.43514258',
               '667be670c7f740.52758876',
               '667bfdfeab6d34.51534194',
               '667bff2df379b5.53081304',
               '667bffb3b3ae66.16138506',
               '667c05ad3595d9.00092026',
               '667e677c217958.45562798',
               '667e677c2549e8.85289343',
               '667c07a988c680.36467497',
               '667e677c2bddd7.76320522',
               '667c0867052b10.12209224',
               '667e58d91b6379.53203432',
               '667c09221b1994.79645670',
               '667e677c1e25e7.27858012',
               '667c0caff0c527.66621614',
               '667e58d9166f67.75643219',
               '667e58d91402f9.55869379',
               '667c0d7c1a2c25.42171062',
               '667e58d918dfe6.23747237',
               '667c09c03bb026.40883695',
               '667c0f783366a2.15185331',
               '667e677c2f4e53.85361321',
               '667e58d8e67dc9.69173999',
               '667e58d8e8a9f3.26329150',
               '667e58d8eaefe0.18391362',
               '667e58d8efebc2.38937885',
               '667e58d9004242.97860565',
               '667e58d904aea6.48830596',
               '667e58d8f20555.60582824',
               '667d31828576d8.46037940',
               '667d320e166875.30973434',
               '667d3293d6fcc2.53026792',
               '667c065f45a327.55067013',
               '667d2fe49edd63.94185560',
               '667d2d726d34d9.80543124',
               '667d2ed3431ed1.79929882',
               '667d2b22923911.57953310',
               '667e677c722cd4.54466988',
               '667c1208be16e3.98383881',
               '667c485f88cb41.11683168',
               '667d1cd9150f44.31238978',
               '667d1f47aca158.41077537',
               '667c12bb905a58.52710727',
               '667d1921657499.98433906',
               '667e6dd7dd4a69.18470849',
               '667d2678db47c2.73895222',
               '667c1332cd8232.01161681',
               '667c14616ac802.18010687',
               '667c03d72b1502.67552912',
               '667c15626a3e40.50715063',
               '667d29d704db37.12173206',
               '667e677c3950d9.96416684',
               '667e677c3cbac5.50389286',
               '667d15b1ac09a7.11635501',
               '667e677c408dd7.97426812',
               '667e677c587561.43422097',
               '667d17335293c2.93969318',
               '667e6dd8602869.69317036',
               '667e6dd8418eb0.29956026',
               '667e6dd848adf1.98125995',
               '667e6dd84c56d1.57393902',
               '667e6dd85d3ca6.45572149',
               '667e6dd8632305.25075935',
               '667cfde9845216.22492904',
               '667c1947cf8119.42008676',
               '667e677c6978f5.52670606',
               '667c1864225670.88486374'
               ]
    try:
        query = {
            "id": {"$in": sensor_ids},
            "type": "AC",
            "admin_status": {"$in": ["N", "S", "U"]}
        }

        projection = {"asset_id": 1, 'id' : 1, 'UOM': 1, "_id": 0}
        data = collection_name7.find(query, projection)
        sensor_list = [{'uuid': item['id'], 'sensorName': item['asset_id'], "UOM": item['UOM']} for item in
                       data]
        return jsonify({"rc": 0, "message": "Success", 'sensorList': sensor_list})

    except Exception as e:
        logs_config.logger.error("Error fetching sensor IDs:", exc_info=True)
        return jsonify({"error": str(e)}), 500

@router.route('/getPredDataDaily', methods=['GET'])
def getPredDataDaily():
    try:
        # Access parameters from the query string
        todo_id = request.args.get('id')
        date = request.args.get('date')

        month_from_date = (datetime.strptime(date, '%Y-%m-%d')).month
        month_today = (datetime.now()).month

        start_date = datetime.strptime(date + " 00:00:00", "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
        end_date = datetime.strptime(date + " 23:59:59", "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")


        # Concatenate todo_id and date to create a new identifier
        id = todo_id + "_" + date
        query = {'_id': id}
        l1 = []

        url = "http://jpdclmdm.radius-ami.com:8850/gtDta"
        headers = {
            "Content-Type": "application/json",
            "token": "yomUE5MXM52pDri0zd44QLonEJFpkgGdsFJrakW1CZ966zYwEIKv8qEp57+1q+QJ9lcbiMlvF6IPVO2kA31Wi9keJAAGP0E3mlTyxmXlto+GQNNcobIPJCk0umanOKfRo3rVXcDf2Z0/iNaYtv1chqh2ou0VFjnvw+//opyhMfz80CoZv2z6OJBBH5eJbXHKA/GdTBmEd2ELB7Nkv3oMkeAq4C8KaTRuriYBWgcKaI4gDGapkvg+IxwBeTkigc7/D34a0VSUr3CklolWayTf0ae04l+/DMVuMVXOGnrIRVF3rpEGICA+8Z55wkd9fAJhCWf3GGsU2bf1hgzwttlS9SHRbSgLa67WQDXzgLGe9W2zaKACAVIN0bS+8KRqQT1wDhVVQUaFkUVZyH6kEQrfow==",
            "api_gateway": "AMI",
            "APIAgent": "shubh"
        }

        params = {
            "sensor_id": todo_id,
            "type": "LP",
            "count": "0",
            "sub_type": "FDR",
            "r_count": "5000"
        }
        response = requests.post(url, json=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        l1.append(data['DATA'])

        columns = ['sensor', 'Clock', 'R_Current', 'Y_Current', 'B_Current', 'R_Voltage', 'Y_Voltage', 'B_Voltage',
                   'Kwh', 'BlockEnergy-WhExp', 'BlockEnergy-VArhQ1', 'BlockEnergy-VArhQ2', 'BlockEnergy-VArhQ3',
                   'BlockEnergy-VArhQ4', 'BlockEnergy-VAhImp',
                   'BlockEnergy-VAhExp', 'MeterHealthIndicator']

        datalist = [(entry['sensor_id'], entry['raw_data']) for i in range(len(l1)) for entry in l1[i]]
        df = pd.DataFrame([row[0].split(',') + row[1].split(',') for row in datalist], columns=columns)
        df = df.drop(['sensor', 'R_Current', 'Y_Current', 'B_Current', 'R_Voltage', 'Y_Voltage', 'B_Voltage',
                    'BlockEnergy-WhExp', 'BlockEnergy-VArhQ1', 'BlockEnergy-VArhQ2', 'BlockEnergy-VArhQ3',
                   'BlockEnergy-VArhQ4', 'BlockEnergy-VAhImp',
                   'BlockEnergy-VAhExp', 'MeterHealthIndicator'], axis=1)

        start_time = pd.to_datetime(start_date)
        end_time = pd.to_datetime(end_date)
        df['Clock'] = pd.to_datetime(df['Clock'])
        df['Kwh'] = pd.to_numeric(df['Kwh'])
        filtered_df = df.loc[(df['Clock'] >= start_time) & (df['Clock'] <= end_time)]
        # filtered_df.sort_values(by = [df['Clock']])
        filtered_df.set_index(['Clock'], inplace=True, drop=True)
        df1 = (filtered_df[['Kwh']].resample(rule="1H").sum())
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
        pd.set_option('display.max_columns', 5000)

        # Check if predicted data exists
        todos_pred = list(collection_name13.find(query, {'_id': 0, 'data': 1}))

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
