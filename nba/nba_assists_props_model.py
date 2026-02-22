#!/usr/bin/env python3
"""NBA Assists Props Model - Wrapper for shared engine"""
from nba_props_shared import NBAPropsEngine

if __name__ == "__main__":
    engine = NBAPropsEngine("assists")
    engine.run()

def grade_pending_picks():
    engine = NBAPropsEngine("assists")
    return engine.grade_pending_picks()

def main():
    engine = NBAPropsEngine("assists")
    engine.run()
