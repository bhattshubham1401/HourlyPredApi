from pydantic import BaseModel


class Todo(BaseModel):
    sensor_id: str
    creation_time: str
    data: str
