import pandas as pd
import numpy as np
import os
import glob
from tqdm import tqdm
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# CONFIGURATION
# ==========================================
# Look for data in the parent directory where data usually lives
DATA_DIR = '../data'
QUESTIONS_PATH = os.path.join(DATA_DIR, 'questions.csv')
USER_DATA_DIR = os.path.join(DATA_DIR, 'kt1')

# Output settings
MAX_SEQ_LEN = 100
MIN_INTERACTIONS = 20 
NUM_USERS_TO_PROCESS = 2000
STRIDE = 50

output_sequences = 'general_sequences.npy'
output_metadata = 'general_metadata.npz'


# ==========================================
# PART 1: LOAD AND PREP METADATA
# ==========================================
def load_and_prep_questions():
    """Load question metadata and create lookup dictionary."""
    print("Loading Question Metadata...")
    df_q = pd.read_csv(QUESTIONS_PATH)

    def extract_concept(tags_str):
        if pd.isna(tags_str) or tags_str == 'nan':
            return -1
        try:
            return int(str(tags_str).split(';')[0])
        except:
            return -1

    df_q['concept'] = df_q['tags'].apply(extract_concept)
    q_dict = df_q.set_index('question_id')[['correct_answer', 'part', 'concept']].to_dict('index')

    return q_dict, df_q


# ==========================================
# PART 2: CALCULATE GLOBAL DIFFICULTY
# ==========================================
def calculate_question_difficulty(user_files, q_dict, sample_size=1000):
    print(f"\nCalculating Global Difficulty using {sample_size} users...")

    question_stats = {}  
    files_to_scan = user_files[:sample_size]

    for f_path in tqdm(files_to_scan, desc="Scanning users"):
        try:
            df = pd.read_csv(f_path)
            for _, row in df.iterrows():
                qid = row['question_id']
                u_ans = row['user_answer']

                if qid not in q_dict:
                    continue

                correct_ans = q_dict[qid]['correct_answer']
                is_correct = 1 if u_ans == correct_ans else 0

                if qid not in question_stats:
                    question_stats[qid] = [0, 0]

                question_stats[qid][0] += is_correct
                question_stats[qid][1] += 1
        except Exception as e:
            continue

    difficulty_map = {}
    question_frequency = {}

    for qid, stats in question_stats.items():
        total = stats[1]
        correct = stats[0]

        if total >= 5: 
            difficulty = 1.0 - ((correct + 1) / (total + 2))
            difficulty_map[qid] = np.clip(difficulty, 0.1, 0.9) 
            question_frequency[qid] = total
        else:
            difficulty_map[qid] = 0.5 
            question_frequency[qid] = total

    return difficulty_map, question_frequency


# ==========================================
# PART 3: PROCESS USER FILES INTO SEQUENCES
# ==========================================
def process_data():
    all_files = glob.glob(os.path.join(USER_DATA_DIR, 'u*.csv'))

    if not all_files:
        raise FileNotFoundError(f"No user files found in {USER_DATA_DIR}!")

    all_files = sorted(all_files, key=lambda x: int(x.split('u')[-1].split('.')[0]))
    q_dict, df_questions = load_and_prep_questions()
    difficulty_map, question_freq = calculate_question_difficulty(
        all_files, q_dict, sample_size=min(1000, len(all_files))
    )

    sequences = []
    users_processed = 0
    users_skipped = 0
    total_interactions = 0

    files_to_process = all_files[:NUM_USERS_TO_PROCESS]

    for f_path in tqdm(files_to_process, desc="Processing users"):
        try:
            df = pd.read_csv(f_path)
            if len(df) < MIN_INTERACTIONS:
                users_skipped += 1
                continue

            # Core mapping
            df['correct_answer'] = df['question_id'].map(lambda x: q_dict.get(x, {}).get('correct_answer', 'a'))
            df['is_correct'] = (df['user_answer'] == df['correct_answer']).astype(int)
            df['difficulty'] = df['question_id'].map(difficulty_map).fillna(0.5)
            df['concept'] = df['question_id'].map(lambda x: q_dict.get(x, {}).get('concept', -1))

            # Time Features
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['lag_time'] = (df['timestamp'] - df['timestamp'].shift(1)).dt.total_seconds()
            df['lag_time'] = df['lag_time'].fillna(0).clip(upper=3600)  
            df['lag_time_norm'] = np.log1p(df['lag_time']) / np.log1p(3600)  

            df['elapsed_time'] = df['elapsed_time'].fillna(df['elapsed_time'].median())
            df['elapsed_time'] = df['elapsed_time'].clip(upper=300000) 
            df['elapsed_time_norm'] = df['elapsed_time'] / 300000.0

            # --- DOMAIN AGNOSTIC FEATURE ---
            # Instead of specific part/concept ID, track if the concept CHANGED
            df['is_new_concept'] = (df['concept'] != df['concept'].shift(1)).astype(int)

            feature_cols = [
                'is_correct',        # 0: Target variable
                'difficulty',        # 1: Question difficulty
                'elapsed_time_norm', # 2: Time spent (normalized)
                'lag_time_norm',     # 3: Time since last Q (normalized)
                'is_new_concept',    # 4: Domain agnostic module transition indicator
            ]

            user_matrix = df[feature_cols].values.astype(np.float32)
            total_interactions += len(user_matrix)

            seq_len = MAX_SEQ_LEN
            if len(user_matrix) < seq_len:
                padding = np.zeros((seq_len - len(user_matrix), len(feature_cols)))
                user_matrix = np.vstack([padding, user_matrix])
                sequences.append(user_matrix)
            else:
                for i in range(0, len(user_matrix) - seq_len + 1, STRIDE):
                    seq_block = user_matrix[i:i + seq_len]
                    sequences.append(seq_block)

            users_processed += 1

        except Exception as e:
            users_skipped += 1
            continue

    final_data = np.array(sequences, dtype=np.float32)

    np.save(output_sequences, final_data)
    np.savez(
        output_metadata,
        difficulty_map=np.array(list(difficulty_map.items()), dtype=object),
        question_freq=np.array(list(question_freq.items()), dtype=object),
    )

    return final_data


if __name__ == "__main__":
    print("=" * 60)
    print("  DOMAIN-AGNOSTIC DATA PREPROCESSING")
    print("=" * 60)
    try:
        processed_data = process_data()
        print("\n🎉 Preprocessing successful!")
    except Exception as e:
        print(f"\n❌ Error during preprocessing: {e}")
