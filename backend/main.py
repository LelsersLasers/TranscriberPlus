import os
import flask
import flask_cors # type: ignore[import]

app = flask.Flask(__name__, static_folder="../frontend/public")

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
@flask_cors.cross_origin()
def serve(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return flask.send_from_directory(app.static_folder, path)
    return flask.send_from_directory(app.static_folder, 'index.html')


if __name__ == "__main__":
    app.run(port=5000, debug=True)