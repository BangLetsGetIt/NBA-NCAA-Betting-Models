#!/usr/bin/env python3
from wnba_props_shared import WNBAPropsEngine

def main():
    WNBAPropsEngine("threes").run()

def grade_pending_picks():
    return WNBAPropsEngine("threes").grade_pending()

if __name__ == "__main__":
    main()
