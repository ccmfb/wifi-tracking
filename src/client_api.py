import io
import sqlite3

from density_map import get_density_image

from flask import Flask, send_file
import pandas as pd


app = Flask(__name__)



@app.route('/density_map/<int:floor_id>/', methods=['GET'])
def get_density_map(floor_id):
    '''
    Get the density map of a floor.
    
    Args:
        floor_id (int): Floor ID.
        
    Returns:
        dict: Density map of the floor.
    '''

    # Loading most recent batch
    batch = get_last_batch()

    # Getting the density map
    density_map_bytes = get_density_image(floor_id=floor_id, batch=batch)

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