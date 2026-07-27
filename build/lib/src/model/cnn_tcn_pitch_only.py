
"""Pitch-only model.

Key changes:
- Remove onset/attack/active/release heads.
- Replace GlobalAveragePooling1D with:
    x = x[:, -1, :]
- Single softmax output for pitch.
"""
