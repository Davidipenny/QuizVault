import os
import tempfile


os.environ["QUIZVAULT_DATA_DIR"] = tempfile.mkdtemp(prefix="quizvault-test-")
