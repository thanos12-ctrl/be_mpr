"""
LSTM Student Simulator Model
"""

import torch
import torch.nn as nn


class StudentSimulator(nn.Module):
    """LSTM Student Simulator"""

    def __init__(self, input_dim=5, hidden_dim=128, num_layers=2, dropout=0.3):
        super(StudentSimulator, self).__init__()
        self.lstm = nn.LSTM(
            input_dim, hidden_dim, num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_dim, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        out, _ = self.lstm(x)
        out = self.dropout(out)
        out = self.fc(out[:, -1, :])
        return self.sigmoid(out).squeeze(-1)
