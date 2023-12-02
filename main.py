from flask import Flask
from routes.routes import router
from flask_cors import CORS

app = Flask(__name__)
CROS(app)
app.register_blueprint(router)

if __name__ == "__main__":
    app.run(debug=True)

