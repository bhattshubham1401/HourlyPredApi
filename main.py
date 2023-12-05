from flask import Flask
from routes.routes import router
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
app.register_blueprint(router)

if __name__ == "__main__":
    app.run(debug=True)