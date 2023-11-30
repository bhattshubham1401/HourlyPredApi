from flask import Flask
from routes.routes import router

app = Flask(__name__)
app.register_blueprint(router)

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=8081)

