db = []

def store(vec, text):
    db.append((vec, text))

def get():
    return db