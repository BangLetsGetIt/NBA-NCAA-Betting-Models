#!/usr/bin/env python3
"""NBA 3-Pointers Props Model - Wrapper for shared engine"""
from nba_props_shared import NBAPropsEngine

if __name__ == "__main__":
    engine = NBAPropsEngine("threes")
    engine.run()

def grade_pending_picks():
    engine = NBAPropsEngine("threes")
    return engine.grade_pending_picks()

def main():
    engine = NBAPropsEngine("threes")
    engine.run()
