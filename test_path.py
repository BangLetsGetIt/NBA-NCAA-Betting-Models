from pathlib import Path
import os

print(f"File: {__file__}")
p = Path(__file__)
print(f"Path: {p}")
print(f"Parent: {p.parent}")
print(f"Parent.Parent: {p.parent.parent}")
print(f"Resolve: {p.resolve()}")
print(f"Resolve Parent: {p.resolve().parent}")
print(f"Resolve Parent Parent: {p.resolve().parent.parent}")
