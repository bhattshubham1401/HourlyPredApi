def individual_serial(todo) -> dict:
    return {
        "id": str(todo["_id"]),
        "sensor_id": todo["sensor_id"],
        "creation_time": todo["creation_time"],
        "data": todo["data"]
    }


def list_serial(todos) -> list:
    return [individual_serial(todo) for todo in todos]
