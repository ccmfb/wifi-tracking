import io
import sqlite3

from density_map import get_density_image

from flask import Flask, send_file, request
import pandas as pd
from dotenv import dotenv_values


app = Flask(__name__)
API_KEY = dotenv_values('../.env')['DENSITY_MAP_API_KEY']


def require_api_key(f):
    def decorator(*args, **kwargs):
        # Get the key from the request headers
        api_key = request.headers.get('x-api-key')
        if api_key and api_key == API_KEY:
            return f(*args, **kwargs)
        else:
            return jsonify({"error": "Invalid or missing API key"}), 403
    return decorator


@app.route('/density_map/<int:floor_id>/', methods=['GET'])
@require_api_key
def get_density_map(floor_id):
    '''
    Get the density map of a floor.
    
    Args:
        floor_id (int): Floor ID.
        
    Returns:
        dict: Density map of the floor.
    '''

    # Get query parameters
    dpi = request.args.get('dpi', default=200, type=int)

    color1 = request.args.get('color1', default='[100,0,0]')
    color2 = request.args.get('color2', default='[0,100,0]')
    color3 = request.args.get('color3', default='[0,0,100]')

    color1 = color1.replace('[','').replace(']','').split(',')
    color2 = color2.replace('[','').replace(']','').split(',')
    color3 = color3.replace('[','').replace(']','').split(',')

    color1 = [int(color) for color in color1]
    color2 = [int(color) for color in color2]
    color3 = [int(color) for color in color3]

    custom_colors = [color1, color2, color3]
    alpha = request.args.get('alpha', default=0.6, type=float)
    plot_devices = request.args.get('plot_devices', default=False, type=bool)

    # Loading most recent batch
    batch = get_last_batch()

    # Getting the density map
    density_map_bytes = get_density_image(
        floor_id=floor_id, 
        batch=batch,
        dpi=dpi,
        custom_colors=custom_colors,
        alpha=alpha,
        plot_devices=plot_devices
    )

    return send_file(
        io.BytesIO(density_map_bytes),
        mimetype='image/png',
        as_attachment=False,
    )


def get_last_batch() -> pd.DataFrame:
    '''
    Get the most recent batch of data.
    
    Returns:
        pd.DataFrame: Most recent batch of data.
    '''

    conn = sqlite3.connect('../data/refined_data.db')
    cursor = conn.cursor()

    cursor.execute("SELECT timestamp FROM data_refined ORDER BY id DESC LIMIT 1")
    timestamp = cursor.fetchone()[0]

    cursor.execute("SELECT * FROM data_refined WHERE timestamp = ?", (timestamp,))
    rows = cursor.fetchall()
    descritions = [description[0] for description in cursor.description]

    conn.close()

    batch = pd.DataFrame(rows, columns=descritions)
    batch['floor_id'] = batch['floor_id'].astype(int)
    batch['room_id'] = batch['room_id'].astype(str)

    return batch


if __name__ == '__main__':
    app.run(debug=True)