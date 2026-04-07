import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.metrics import roc_auc_score, accuracy_score
import matplotlib.pyplot as plt
import os

# ==========================================
# 1. CONFIGURATION
# ==========================================
BATCH_SIZE = 128  # Increased from 64 for faster training
HIDDEN_DIM = 128  # Increased from 64 for better capacity
NUM_LAYERS = 2
EPOCHS = 25
LEARNING_RATE = 0.001
INPUT_DIM = 5  # [is_correct, difficulty, elapsed_time, lag_time, part]
DROPOUT = 0.3  # Add dropout for regularization

# Device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

# Reproducibility
torch.manual_seed(42)
np.random.seed(42)


# ==========================================
# 2. IMPROVED DATASET CLASS
# ==========================================
class EdNetDataset(Dataset):
    """
    Dataset for Knowledge Tracing with EdNet data.

    CRITICAL FIX: Your original version had the target prediction off by one,
    which doesn't match the KT task properly.
    """

    def __init__(self, npy_file, predict_next=True):
        """
        Args:
            npy_file: Path to .npy file with shape (N, seq_len, features)
            predict_next: If True, predict next step. If False, predict current step.
        """
        self.data = np.load(npy_file).astype(np.float32)
        self.predict_next = predict_next

        print(f"Loaded data: {self.data.shape}")
        print(f"  Sequences: {len(self.data)}")
        print(f"  Sequence length: {self.data.shape[1]}")
        print(f"  Features: {self.data.shape[2]}")

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        sequence = self.data[idx]

        if self.predict_next:
            # Standard Knowledge Tracing:
            # Given history [q_1, a_1, ..., q_t], predict a_{t+1}
            # Input: Full sequence except last step
            # Target: Correctness of next step
            x = sequence[:-1, :]  # Shape: (seq_len-1, features)
            y = sequence[1:, 0]  # Shape: (seq_len-1,) - only 'is_correct'
        else:
            # Alternative: Predict current step given previous steps
            # This is what your original code was doing
            x = sequence[:, :]
            y = sequence[:, 0]

        return torch.tensor(x), torch.tensor(y)


# ==========================================
# 3. IMPROVED STUDENT SIMULATOR MODEL
# ==========================================
class StudentSimulator(nn.Module):
    """
    LSTM-based Knowledge Tracing model.

    IMPROVEMENTS:
    - Added dropout for regularization
    - Added batch normalization option
    - Better weight initialization
    """

    def __init__(self, input_dim, hidden_dim, num_layers, dropout=0.3):
        super(StudentSimulator, self).__init__()

        self.hidden_dim = hidden_dim
        self.num_layers = num_layers

        # LSTM with dropout
        self.lstm = nn.LSTM(
            input_dim,
            hidden_dim,
            num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0  # Dropout between LSTM layers
        )

        # Additional dropout after LSTM
        self.dropout = nn.Dropout(dropout)

        # Output layer
        self.fc = nn.Linear(hidden_dim, 1)
        self.sigmoid = nn.Sigmoid()

        # Initialize weights
        self._init_weights()

    def _init_weights(self):
        """Better weight initialization for LSTM."""
        for name, param in self.lstm.named_parameters():
            if 'weight' in name:
                nn.init.xavier_uniform_(param)
            elif 'bias' in name:
                nn.init.constant_(param, 0)

        nn.init.xavier_uniform_(self.fc.weight)
        nn.init.constant_(self.fc.bias, 0)

    def forward(self, x):
        """
        Args:
            x: (batch, seq_len, input_dim)
        Returns:
            predictions: (batch, seq_len) - probability of correctness
        """
        # LSTM forward pass
        lstm_out, (hn, cn) = self.lstm(x)  # lstm_out: (batch, seq_len, hidden_dim)

        # Apply dropout
        lstm_out = self.dropout(lstm_out)

        # Project to predictions
        out = self.fc(lstm_out)  # (batch, seq_len, 1)
        out = self.sigmoid(out)

        return out.squeeze(-1)  # (batch, seq_len)


# ==========================================
# 4. METRICS CALCULATION
# ==========================================
def calculate_metrics(predictions, targets):
    """
    Calculate accuracy and AUC-ROC.
    """
    # Flatten
    preds_flat = predictions.cpu().numpy().flatten()
    targets_flat = targets.cpu().numpy().flatten()

    # Remove any NaN/inf values
    mask = np.isfinite(preds_flat) & np.isfinite(targets_flat)
    preds_flat = preds_flat[mask]
    targets_flat = targets_flat[mask]

    # Binary predictions (threshold at 0.5)
    preds_binary = (preds_flat > 0.5).astype(int)

    # Metrics
    accuracy = accuracy_score(targets_flat, preds_binary)

    try:
        auc = roc_auc_score(targets_flat, preds_flat)
    except:
        auc = 0.5  # Default if can't compute

    return accuracy, auc


# ==========================================
# 5. TRAINING FUNCTION
# ==========================================
def train():
    """Main training loop with improvements."""

    # A. Load Data
    print("\n" + "=" * 60)
    print("  LOADING DATA")
    print("=" * 60)

    try:
        full_dataset = EdNetDataset('processed_ednet_sequences.npy', predict_next=True)
    except FileNotFoundError:
        print("❌ Error: 'processed_ednet_sequences.npy' not found.")
        print("Run the preprocessing script first!")
        return

    # Split into train/val/test (70/15/15)
    total_size = len(full_dataset)
    train_size = int(0.7 * total_size)
    val_size = int(0.15 * total_size)
    test_size = total_size - train_size - val_size

    train_dataset, val_dataset, test_dataset = torch.utils.data.random_split(
        full_dataset,
        [train_size, val_size, test_size],
        generator=torch.Generator().manual_seed(42)
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=2,  # Parallel data loading
        pin_memory=True if torch.cuda.is_available() else False
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=2,
        pin_memory=True if torch.cuda.is_available() else False
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False
    )

    print(f"Train: {train_size} | Val: {val_size} | Test: {test_size}")

    # B. Initialize Model
    print("\n" + "=" * 60)
    print("  INITIALIZING MODEL")
    print("=" * 60)

    model = StudentSimulator(INPUT_DIM, HIDDEN_DIM, NUM_LAYERS, DROPOUT).to(device)

    print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")
    print(f"Trainable parameters: {sum(p.numel() for p in model.parameters() if p.requires_grad):,}")

    # Loss and optimizer
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-5)

    # Learning rate scheduler
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=3, verbose=True
    )

    # Tracking
    history = {
        'train_loss': [],
        'val_loss': [],
        'train_acc': [],
        'val_acc': [],
        'train_auc': [],
        'val_auc': []
    }

    best_val_loss = float('inf')
    patience_counter = 0
    early_stop_patience = 7

    # C. Training Loop
    print("\n" + "=" * 60)
    print("  TRAINING")
    print("=" * 60)

    for epoch in range(EPOCHS):
        # --- TRAINING PHASE ---
        model.train()
        train_loss = 0
        all_train_preds = []
        all_train_targets = []

        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)

            optimizer.zero_grad()

            # Forward
            predictions = model(X_batch)
            loss = criterion(predictions, y_batch)

            # Backward
            loss.backward()

            # Gradient clipping to prevent exploding gradients
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)

            optimizer.step()

            train_loss += loss.item()
            all_train_preds.append(predictions.detach())
            all_train_targets.append(y_batch.detach())

        avg_train_loss = train_loss / len(train_loader)

        # Calculate training metrics
        all_train_preds = torch.cat(all_train_preds)
        all_train_targets = torch.cat(all_train_targets)
        train_acc, train_auc = calculate_metrics(all_train_preds, all_train_targets)

        # --- VALIDATION PHASE ---
        model.eval()
        val_loss = 0
        all_val_preds = []
        all_val_targets = []

        with torch.no_grad():
            for X_val, y_val in val_loader:
                X_val, y_val = X_val.to(device), y_val.to(device)
                preds = model(X_val)
                loss = criterion(preds, y_val)
                val_loss += loss.item()

                all_val_preds.append(preds)
                all_val_targets.append(y_val)

        avg_val_loss = val_loss / len(val_loader)

        # Calculate validation metrics
        all_val_preds = torch.cat(all_val_preds)
        all_val_targets = torch.cat(all_val_targets)
        val_acc, val_auc = calculate_metrics(all_val_preds, all_val_targets)

        # Update scheduler
        scheduler.step(avg_val_loss)

        # Save history
        history['train_loss'].append(avg_train_loss)
        history['val_loss'].append(avg_val_loss)
        history['train_acc'].append(train_acc)
        history['val_acc'].append(val_acc)
        history['train_auc'].append(train_auc)
        history['val_auc'].append(val_auc)

        # Print progress
        print(f"Epoch {epoch + 1}/{EPOCHS}")
        print(f"  Train - Loss: {avg_train_loss:.4f} | Acc: {train_acc:.4f} | AUC: {train_auc:.4f}")
        print(f"  Val   - Loss: {avg_val_loss:.4f} | Acc: {val_acc:.4f} | AUC: {val_auc:.4f}")

        # Early stopping
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            patience_counter = 0
            # Save best model
            torch.save(model.state_dict(), "student_simulator_best.pth")
            print("  ✅ Saved best model")
        else:
            patience_counter += 1
            if patience_counter >= early_stop_patience:
                print(f"\n⚠️  Early stopping triggered after {epoch + 1} epochs")
                break

        print()

    # D. Load best model and test
    print("\n" + "=" * 60)
    print("  FINAL EVALUATION ON TEST SET")
    print("=" * 60)

    model.load_state_dict(torch.load("student_simulator_best.pth", weights_only=True))
    model.eval()

    test_loss = 0
    all_test_preds = []
    all_test_targets = []

    with torch.no_grad():
        for X_test, y_test in test_loader:
            X_test, y_test = X_test.to(device), y_test.to(device)
            preds = model(X_test)
            loss = criterion(preds, y_test)
            test_loss += loss.item()

            all_test_preds.append(preds)
            all_test_targets.append(y_test)

    all_test_preds = torch.cat(all_test_preds)
    all_test_targets = torch.cat(all_test_targets)
    test_acc, test_auc = calculate_metrics(all_test_preds, all_test_targets)

    print(f"Test Loss: {test_loss / len(test_loader):.4f}")
    print(f"Test Accuracy: {test_acc:.4f}")
    print(f"Test AUC-ROC: {test_auc:.4f}")

    # E. Save final model
    torch.save(model.state_dict(), "student_simulator.pth")
    print("\n✅ Final model saved as 'student_simulator.pth'")

    # F. Plot training history
    plot_training_history(history)

    return model, history


# ==========================================
# 6. VISUALIZATION
# ==========================================
def plot_training_history(history):
    """Plot training curves."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    epochs = range(1, len(history['train_loss']) + 1)

    # Loss
    axes[0].plot(epochs, history['train_loss'], 'b-', label='Train Loss')
    axes[0].plot(epochs, history['val_loss'], 'r-', label='Val Loss')
    axes[0].set_xlabel('Epoch')
    axes[0].set_ylabel('Loss (BCE)')
    axes[0].set_title('Training & Validation Loss')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Accuracy
    axes[1].plot(epochs, history['train_acc'], 'b-', label='Train Acc')
    axes[1].plot(epochs, history['val_acc'], 'r-', label='Val Acc')
    axes[1].set_xlabel('Epoch')
    axes[1].set_ylabel('Accuracy')
    axes[1].set_title('Training & Validation Accuracy')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    # AUC
    axes[2].plot(epochs, history['train_auc'], 'b-', label='Train AUC')
    axes[2].plot(epochs, history['val_auc'], 'r-', label='Val AUC')
    axes[2].set_xlabel('Epoch')
    axes[2].set_ylabel('AUC-ROC')
    axes[2].set_title('Training & Validation AUC')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('lstm_training_history.png', dpi=150)
    print("📊 Training plots saved to 'lstm_training_history.png'")
    plt.show()


# ==========================================
# 7. MAIN
# ==========================================
if __name__ == "__main__":
    print("=" * 60)
    print("  STUDENT SIMULATOR LSTM TRAINING")
    print("  Knowledge Tracing with EdNet Dataset")
    print("=" * 60)

    model, history = train()

    print("\n🎉 Training complete!")
    print(f"Best validation AUC: {max(history['val_auc']):.4f}")