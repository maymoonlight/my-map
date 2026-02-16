import pandas as pd
import win32api
import os

curr_path = os.getcwd()
fname = "result.xlsx"
full_path = os.path.join(curr_path, fname)

data = {
    'Task': ['Install', 'Library', 'Run'],
    'Status': ['Done', 'Done', 'Processing']
}
df = pd.DataFrame(data)
df.to_excel(full_path, index=False)

win32api.MessageBox(0, f"Success!\nPath: {full_path}", "ComDoctor", 64)
print("All tasks completed successfully.")