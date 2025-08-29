import hashlib

def generate_entry_hash(entry):
    """
    entry: dict with fields like username, category, outcome, etc.
    """
    # Concatenate the fields into a string (adjust fields as needed)
    hash_input = ",".join([
        entry.get("category", ""),
        entry.get("outcome", ""),
        entry.get("mvp", ""),
        str(entry.get("goals", 0)),
        str(entry.get("shots", 0)),
        str(entry.get("assists", 0)),
        str(entry.get("saves", 0)),
        str(entry.get("mmr", ""))
    ])

    # Generate SHA256 hash (you can use md5 if preferred)
    return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
