"""Tests voor tijdvenster parser."""

import pytest
from ap06_planner.parsers.tijdvenster import parse_tijdvenster, normaliseer_tijd


def test_normaliseer_hele_uren():
    assert normaliseer_tijd("7") == "07:00"
    assert normaliseer_tijd("18") == "18:00"
    assert normaliseer_tijd("12") == "12:00"


def test_normaliseer_met_punt():
    assert normaliseer_tijd("8.30") == "08:30"
    assert normaliseer_tijd("10.30") == "10:30"
    assert normaliseer_tijd("11.30") == "11:30"


def test_parse_standaard():
    tv = parse_tijdvenster("Bladel TonTrans 7-18 LAD17")
    assert tv is not None
    assert tv.plaats == "Bladel"
    assert tv.begintijd == "07:00"
    assert tv.eindtijd == "18:00"
    assert tv.type == "LAD"
    assert tv.nummer == "17"


def test_parse_met_punt_tijdvenster():
    tv = parse_tijdvenster("Eersel VanMeer 8.30-10.30 LAD")
    assert tv is not None
    assert tv.begintijd == "08:30"
    assert tv.eindtijd == "10:30"


def test_parse_los():
    tv = parse_tijdvenster("Marrum JB 7-9 LOS")
    assert tv is not None
    assert tv.type == "LOS"
    assert tv.begintijd == "07:00"
    assert tv.eindtijd == "09:00"


def test_parse_zundert():
    tv = parse_tijdvenster("Zundert Dams 6-18 LAD1")
    assert tv is not None
    assert tv.plaats == "Zundert"
    assert tv.begintijd == "06:00"
    assert tv.eindtijd == "18:00"
    assert tv.nummer == "1"


def test_parse_veendam():
    tv = parse_tijdvenster("Veendam VanOosten 10-12 LAD2")
    assert tv is not None
    assert tv.plaats == "Veendam"
    assert tv.eindtijd == "12:00"


def test_parse_vroeg_tijdstip():
    tv = parse_tijdvenster("Oude-tonge BAX 5.30-7.30 LAD")
    assert tv is not None
    assert tv.begintijd == "05:30"
    assert tv.eindtijd == "07:30"


def test_parse_lege_string():
    assert parse_tijdvenster("") is None
    assert parse_tijdvenster(None) is None


def test_parse_geen_tijdvenster():
    assert parse_tijdvenster("Sommige tekst zonder tijdvenster") is None
