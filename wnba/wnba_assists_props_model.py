#!/usr/bin/env python3
from wnba_props_shared import WNBAPropsEngine

def main():
    WNBAPropsEngine("assists").run()

def grade_pending_picks():
    return WNBAPropsEngine("assists").grade_pending()

if __name__ == "__main__":
    main()
