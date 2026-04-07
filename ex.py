import numpy as np

difficulty_map ={}

try:
    metadata = np.load('ednet_metadata.npz', allow_pickle=True)
    diff_array = metadata['difficulty_map']
    for qid, diff in diff_array:
        difficulty_map[str(qid)] = float(diff)
    print(f"✅ Loaded difficulty for {len(difficulty_map)} questions")
except Exception as e:
    print(f"⚠️  Difficulty map not loaded: {e}")

print(difficulty_map)