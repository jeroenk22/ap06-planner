"""Helper script voor AppTest.from_file — rendert beheer.render() met lege database."""

from unittest.mock import patch

import ap06_planner.pages.beheer as beheer

with patch("ap06_planner.pages.beheer.haal_alle_monsternemers", return_value=[]), \
     patch("ap06_planner.pages.beheer.initialiseer_db"):
    beheer.render()
