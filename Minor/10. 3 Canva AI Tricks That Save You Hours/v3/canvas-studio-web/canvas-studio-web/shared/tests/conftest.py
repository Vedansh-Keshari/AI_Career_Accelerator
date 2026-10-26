import os

os.environ.setdefault("CANVAS_NO_KEYRING", "1")  # tests must never touch the real OS credential store
