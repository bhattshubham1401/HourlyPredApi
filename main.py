from flask import Flask
from routes.routes import router
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
app.register_blueprint(router)

# print(app.register_blueprint(router))

if __name__ == "__main__":
    app.run(debug=True)
    # app.run(debug=True, host="127.0.0.1", port=5000)
