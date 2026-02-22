#!/usr/bin/env python3
"""NBA Points Props Model - Wrapper for shared engine"""
from nba_props_shared import NBAPropsEngine

if __name__ == "__main__":
    engine = NBAPropsEngine("points")
    engine.run()

def grade_pending_picks():
    engine = NBAPropsEngine("points")
    return engine.grade_pending_picks()

def main():
    engine = NBAPropsEngine("points")
    engine.run()
