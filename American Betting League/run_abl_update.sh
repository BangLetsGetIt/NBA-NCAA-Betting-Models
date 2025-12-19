#!/bin/bash
# Wrapper script to update ABL Dashboard
# Intended to be run via cron

cd "/Users/rico/sports-models/American Betting League" || exit
/usr/bin/python3 abl_recap.py >> update_log.txt 2>&1
