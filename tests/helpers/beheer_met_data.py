"""Helper voor AppTest — rendert beheer.render() met één monsternemer in de database."""

from unittest.mock import patch

import ap06_planner.pages.beheer as beheer
from ap06_planner.models.schemas import Monsternemer

_m = Monsternemer(
    id=1,
    code="AP06",
    voornaam="Jan",
    tussenvoegsel=None,
    achternaam="Smit",
    adres="Straat 1",
    postcode="1234AB",
    woonplaats="Amsterdam",
    land="Nederland",
    telefoon="0612345678",
    laadinstructie=None,
    ophaaldagen=["ma", "wo"],
    uiterlijke_tijd=None,
    uiterlijke_plantijd=None,
    bijzonderheden=None,
    aantal_lege_bakken=2,
    sjabloon=False,
    ophalen=True,
)

with (
    patch("ap06_planner.pages.beheer.haal_alle_monsternemers", return_value=[_m]),
    patch("ap06_planner.pages.beheer.initialiseer_db"),
):
    beheer.render()
