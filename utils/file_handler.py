import json

def save_to_file(data):
    with open("backup.json", "w") as f:
        json.dump(data, f)

def load_from_file():
    try:
        with open("backup.json", "r") as f:
            return json.load(f)
    except:
        return {}