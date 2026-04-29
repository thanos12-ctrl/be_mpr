import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.metrics import roc_auc_score, accuracy_score
import matplotlib.pyplot as plt
import os

BATCH_SIZE = 128 
HIDDEN_DIM = 128 
NUM_LAYERS = 2
EPOCHS = 25
LEARNING_RATE = 0.001
INPUT_DIM = 5  # [is_correct, difficulty, elapsed_time, lag_time, is_new_concept]
DROPOUT = 0.3  

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
torch.manual_seed(42)
np.random.seed(42)


class GeneralDataset(Dataset):
    def __init__(self, npy_file):
        self.data = np.load(npy_file).astype(np.float32)
    def __len__(self):
        return len(self.data)
    def __getitem__(self, idx):
        sequence = self.data[idx]
        x = sequence[:-1, :]  
        y = sequence[1:, 0]  
        return torch.tensor(x), torch.tensor(y)


class StudentSimulator(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_layers, dropout=0.3):
        super(StudentSimulator, self).__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True, dropout=dropout if num_layers > 1 else 0)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_dim, 1)
        self.sigmoid = nn.Sigmoid()
        self._init_weights()

    def _init_weights(self):
        for name, param in self.lstm.named_parameters():
            if 'weight' in name:
                nn.init.xavier_uniform_(param)
            elif 'bias' in name:
                nn.init.constant_(param, 0)
        nn.init.xavier_uniform_(self.fc.weight)
        nn.init.constant_(self.fc.bias, 0)

    def forward(self, x):
        lstm_out, _ = self.lstm(x)  
        lstm_out = self.dropout(lstm_out)
        out = self.fc(lstm_out)  
        out = self.sigmoid(out)
        return out.squeeze(-1) 


def calculate_metrics(predictions, targets):
    preds_flat = predictions.cpu().numpy().flatten()
    targets_flat = targets.cpu().numpy().flatten()
    mask = np.isfinite(preds_flat) & np.isfinite(targets_flat)
    preds_flat = preds_flat[mask]
    targets_flat = targets_flat[mask]
    preds_binary = (preds_flat > 0.5).astype(int)
    accuracy = accuracy_score(targets_flat, preds_binary)
    try:
        auc = roc_auc_score(targets_flat, preds_flat)
    except:
        auc = 0.5 
    return accuracy, auc


def train():
    try:
        full_dataset = GeneralDataset('general_sequences.npy')
    except FileNotFoundError:
        print("❌ Error: 'general_sequences.npy' not found. Run preprocessing.py first!")
        return

    total_size = len(full_dataset)
    train_size = int(0.7 * total_size)
    val_size = int(0.15 * total_size)
    test_size = total_size - train_size - val_size

    train_dataset, val_dataset, test_dataset = torch.utils.data.random_split(
        full_dataset, [train_size, val_size, test_size], generator=torch.Generator().manual_seed(42)
    )

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)

    model = StudentSimulator(INPUT_DIM, HIDDEN_DIM, NUM_LAYERS, DROPOUT).to(device)
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-5)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=3, verbose=True)

    best_val_loss = float('inf')
    patience_counter = 0

    for epoch in range(EPOCHS):
        model.train()
        train_loss = 0
        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            optimizer.zero_grad()
            predictions = model(X_batch)
            loss = criterion(predictions, y_batch)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()
            train_loss += loss.item()

        model.eval()
        val_loss = 0
        with torch.no_grad():
            for X_val, y_val in val_loader:
                X_val, y_val = X_val.to(device), y_val.to(device)
                preds = model(X_val)
                loss = criterion(preds, y_val)
                val_loss += loss.item()

        avg_val_loss = val_loss / len(val_loader)
        scheduler.step(avg_val_loss)

        print(f"Epoch {epoch + 1}/{EPOCHS} | Train Loss: {train_loss / len(train_loader):.4f} | Val Loss: {avg_val_loss:.4f}")

        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            patience_counter = 0
            torch.save(model.state_dict(), "general_student_simulator.pth")
        else:
            patience_counter += 1
            if patience_counter >= 7:
                break

    print("Training complete! Model saved to general_student_simulator.pth")

if __name__ == "__main__":
    train()
