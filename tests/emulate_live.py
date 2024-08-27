import sys
sys.path.append('../src')
sys.path.append('..')

from main import generate_refined_data

from tqdm import tqdm
import pandas as pd


# Reset stored data
with open('../src/init.py') as f:
    code = compile(f.read(), '../src/init.py', 'exec')
    exec(code)


df = pd.read_csv('../data/data.csv')
df = df.sort_values(by='timestamp', ascending=True)
df = df.reset_index(drop=True)
df.head()


timestamps = df['timestamp'].to_numpy()
cutoff_indices = [0]

prev_timestamp = timestamps[0]
for i, timestamp in enumerate(timestamps):

    if timestamp - prev_timestamp > 60*5:
        cutoff_indices.append(i)
        prev_timestamp = timestamp

    # if len(cutoff_indices) == 2*6*6*1:
        # break

#print(cutoff_indices)
batches = []

print('Generating batches...')
for i in tqdm(range(len(cutoff_indices))):
    if i == len(cutoff_indices) - 1:
        break

    batch = df.iloc[cutoff_indices[i]:cutoff_indices[i+1]]
    batches.append(batch)


print('Generating refined data')
for i, batch in enumerate(tqdm(batches)):
    if i == 0:
        generate_refined_data(batch, first_batch=True)
    else:
        generate_refined_data(batch)