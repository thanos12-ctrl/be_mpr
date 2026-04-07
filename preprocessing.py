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
DATA_DIR = './data'
QUESTIONS_PATH = os.path.join(DATA_DIR, 'questions.csv')
USER_DATA_DIR = os.path.join(DATA_DIR, 'kt1')

# Output settings
MAX_SEQ_LEN = 100
MIN_INTERACTIONS = 20  # Increased from 10 - need enough history
NUM_USERS_TO_PROCESS = 2000  # Process more users for better model
STRIDE = 50  # Window sliding stride

output_sequences = 'processed_ednet_sequences.npy'
output_metadata = 'ednet_metadata.npz'


# ==========================================
# PART 1: LOAD AND PREP METADATA
# ==========================================
def load_and_prep_questions():
    """Load question metadata and create lookup dictionary."""
    print("Loading Question Metadata...")
    df_q = pd.read_csv(QUESTIONS_PATH)

    print(f"Total questions in database: {len(df_q)}")

    # Extract first tag as concept ID
    def extract_concept(tags_str):
        if pd.isna(tags_str) or tags_str == 'nan':
            return -1
        try:
            return int(str(tags_str).split(';')[0])
        except:
            return -1

    df_q['concept'] = df_q['tags'].apply(extract_concept)

    # Create lookup dictionary
    q_dict = df_q.set_index('question_id')[['correct_answer', 'part', 'concept']].to_dict('index')

    print(f"Loaded {len(q_dict)} questions")
    print(f"Parts: {df_q['part'].unique()}")
    print(f"Unique concepts: {df_q['concept'].nunique()}")

    return q_dict, df_q


# ==========================================
# PART 2: CALCULATE GLOBAL DIFFICULTY
# ==========================================
def calculate_question_difficulty(user_files, q_dict, sample_size=1000):
    """
    Calculate difficulty based on global success rates.
    Difficulty = 1 - (Correct Count / Total Attempts)

    IMPROVED: Also tracks question frequency for filtering
    """
    print(f"\nCalculating Global Difficulty using {sample_size} users...")

    question_stats = {}  # {qid: [correct_count, total_count]}
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

    # Compute difficulty with smoothing
    difficulty_map = {}
    question_frequency = {}

    for qid, stats in question_stats.items():
        total = stats[1]
        correct = stats[0]

        if total >= 5:  # Only use questions with enough data
            # Add Laplace smoothing to avoid extreme values
            difficulty = 1.0 - ((correct + 1) / (total + 2))
            difficulty_map[qid] = np.clip(difficulty, 0.1, 0.9)  # Bound between 0.1-0.9
            question_frequency[qid] = total
        else:
            difficulty_map[qid] = 0.5  # Default for rare questions
            question_frequency[qid] = total

    print(f"Computed difficulty for {len(difficulty_map)} questions")
    print(f"Difficulty stats: min={min(difficulty_map.values()):.3f}, "
          f"max={max(difficulty_map.values()):.3f}, "
          f"mean={np.mean(list(difficulty_map.values())):.3f}")

    return difficulty_map, question_frequency


# ==========================================
# PART 3: PROCESS USER FILES INTO SEQUENCES
# ==========================================
def process_data():
    """Main preprocessing pipeline."""

    # 1. Get user files
    all_files = glob.glob(os.path.join(USER_DATA_DIR, 'u*.csv'))

    if not all_files:
        raise FileNotFoundError(f"No user files found in {USER_DATA_DIR}!")

    # Sort for reproducibility
    all_files = sorted(all_files, key=lambda x: int(x.split('u')[-1].split('.')[0]))
    print(f"\nFound {len(all_files)} user files")

    # 2. Load metadata
    q_dict, df_questions = load_and_prep_questions()
    difficulty_map, question_freq = calculate_question_difficulty(
        all_files, q_dict, sample_size=min(1000, len(all_files))
    )

    # 3. Process users
    sequences = []
    users_processed = 0
    users_skipped = 0
    total_interactions = 0

    print(f"\nProcessing {NUM_USERS_TO_PROCESS} users...")

    files_to_process = all_files[:NUM_USERS_TO_PROCESS]

    for f_path in tqdm(files_to_process, desc="Processing users"):
        try:
            df = pd.read_csv(f_path)

            # Skip users with too few interactions
            if len(df) < MIN_INTERACTIONS:
                users_skipped += 1
                continue

            # --- FEATURE ENGINEERING ---

            # 1. Correctness
            df['correct_answer'] = df['question_id'].map(
                lambda x: q_dict.get(x, {}).get('correct_answer', 'a')
            )
            df['is_correct'] = (df['user_answer'] == df['correct_answer']).astype(int)

            # 2. Difficulty & Metadata
            df['difficulty'] = df['question_id'].map(difficulty_map).fillna(0.5)
            df['part'] = df['question_id'].map(
                lambda x: q_dict.get(x, {}).get('part', 1)
            )
            df['concept'] = df['question_id'].map(
                lambda x: q_dict.get(x, {}).get('concept', -1)
            )

            # 3. Time Features - IMPROVED
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

            # Lag time (time since last question)
            df['lag_time'] = (df['timestamp'] - df['timestamp'].shift(1)).dt.total_seconds()
            df['lag_time'] = df['lag_time'].fillna(0).clip(upper=3600)  # Cap at 1 hour
            df['lag_time_norm'] = np.log1p(df['lag_time']) / np.log1p(3600)  # Normalize to 0-1

            # Elapsed time (time spent on question)
            df['elapsed_time'] = df['elapsed_time'].fillna(df['elapsed_time'].median())
            df['elapsed_time'] = df['elapsed_time'].clip(upper=300000)  # Cap at 5 min
            df['elapsed_time_norm'] = df['elapsed_time'] / 300000.0

            # 4. Additional Features - NEW
            # Running accuracy (helps track learning progress)
            df['running_accuracy'] = df['is_correct'].expanding().mean()

            # Concept-specific accuracy
            df['concept_accuracy'] = df.groupby('concept')['is_correct'].transform(
                lambda x: x.expanding().mean()
            )

            # Question position in session
            df['position'] = np.arange(len(df)) / len(df)

            # --- SEQUENCE CREATION ---
            # Feature columns for LSTM input
            feature_cols = [
                'is_correct',  # 0: Target variable
                'difficulty',  # 1: Question difficulty
                'elapsed_time_norm',  # 2: Time spent (normalized)
                'lag_time_norm',  # 3: Time since last Q (normalized)
                'part',  # 4: Question part (1-7)
            ]

            user_matrix = df[feature_cols].values.astype(np.float32)
            total_interactions += len(user_matrix)

            # Create overlapping windows
            seq_len = MAX_SEQ_LEN

            # If user has fewer interactions than seq_len, pad with zeros
            if len(user_matrix) < seq_len:
                padding = np.zeros((seq_len - len(user_matrix), len(feature_cols)))
                user_matrix = np.vstack([padding, user_matrix])
                sequences.append(user_matrix)
            else:
                # Sliding window approach
                for i in range(0, len(user_matrix) - seq_len + 1, STRIDE):
                    seq_block = user_matrix[i:i + seq_len]
                    sequences.append(seq_block)

            users_processed += 1

        except Exception as e:
            print(f"\nError processing {f_path}: {e}")
            users_skipped += 1
            continue

    # --- SAVE DATA ---
    print(f"\n{'=' * 60}")
    print(f"PREPROCESSING COMPLETE")
    print(f"{'=' * 60}")
    print(f"Users processed: {users_processed}")
    print(f"Users skipped: {users_skipped}")
    print(f"Total interactions: {total_interactions:,}")
    print(f"Sequences generated: {len(sequences)}")
    print(f"Average sequences per user: {len(sequences) / max(users_processed, 1):.1f}")

    # Convert to numpy array
    final_data = np.array(sequences, dtype=np.float32)
    print(f"\nFinal data shape: {final_data.shape}")
    print(f"Memory size: {final_data.nbytes / 1e6:.1f} MB")

    # Save sequences
    np.save(output_sequences, final_data)
    print(f"\n✅ Saved sequences to '{output_sequences}'")

    # Save metadata for later use
    np.savez(
        output_metadata,
        difficulty_map=np.array(list(difficulty_map.items()), dtype=object),  # Use dtype=object for mixed types
        question_freq=np.array(list(question_freq.items()), dtype=object),
        num_concepts=df_questions['concept'].nunique(),
        num_parts=df_questions['part'].nunique()
    )
    print(f"✅ Saved metadata to '{output_metadata}'")

    # Data quality checks
    print(f"\n{'=' * 60}")
    print("DATA QUALITY CHECKS")
    print(f"{'=' * 60}")

    # Check for NaN values
    nan_count = np.isnan(final_data).sum()
    print(f"NaN values: {nan_count} ({nan_count / final_data.size * 100:.3f}%)")

    # Check feature distributions
    print(f"\nFeature Statistics:")
    for i, col in enumerate(feature_cols):
        data_col = final_data[:, :, i].flatten()
        print(f"  {col:<20} - min: {data_col.min():.3f}, "
              f"max: {data_col.max():.3f}, "
              f"mean: {data_col.mean():.3f}")

    return final_data


# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    print("=" * 60)
    print("  EdNet DATA PREPROCESSING")
    print("=" * 60)

    try:
        processed_data = process_data()
        print("\n🎉 Preprocessing successful! Ready for LSTM training.")

    except Exception as e:
        print(f"\n❌ Error during preprocessing: {e}")
        import traceback

        traceback.print_exc()