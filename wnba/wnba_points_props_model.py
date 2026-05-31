#!/usr/bin/env python3
from wnba_props_shared import WNBAPropsEngine

def main():
    WNBAPropsEngine("points").run()

def grade_pending_picks():
    return WNBAPropsEngine("points").grade_pending()

if __name__ == "__main__":
    main()
