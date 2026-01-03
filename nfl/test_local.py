from pathlib import Path
import os
print(f"File: {__file__}")
p = Path(__file__)
print(f"Path: {p}")
print(f"Parent: {p.parent}")
print(f"Parent Parent: {p.parent.parent}")
print(f"Absolute: {p.absolute()}")
print(f"Absolute Parent Parent: {p.absolute().parent.parent}")
