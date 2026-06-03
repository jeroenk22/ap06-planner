"""Datamodellen voor AP06 Planner."""

from dataclasses import dataclass, field


@dataclass
class Monsternemer:
    """Record uit de monsternemer-database."""

    id: int | None
    code: str  # bijv. "AP06"
    voornaam: str
    tussenvoegsel: str | None
    achternaam: str
    adres: str
    postcode: str
    woonplaats: str
    land: str | None
    telefoon: str | None
    laadinstructie: str | None
    ophaaldagen: list[str]  # ["ma", "wo"] etc.
    uiterlijke_tijd: str | None  # "21:30" — wens monsternemer (niet automatisch doorschuiven)
    uiterlijke_plantijd: (
        str | None
    )  # "21:30" — planningtechnische grens (overschreden → doorschuiven)
    bijzonderheden: str | None
    aantal_lege_bakken: int = 2
    sjabloon: bool = False
    ophalen: bool = True  # False = brengt zelf naar lab

    @property
    def volledige_naam(self) -> str:
        delen = [self.voornaam]
        if self.tussenvoegsel:
            delen.append(self.tussenvoegsel)
        delen.append(self.achternaam)
        return " ".join(delen)


@dataclass
class Tijdvenster:
    """Geparsed tijdvenster uit een planningsregel."""

    plaats: str
    klant_naam: str
    begintijd: str  # "07:00"
    eindtijd: str  # "18:00"
    type: str  # "LAD" of "LOS"
    nummer: str | None  # bijv. "17" uit "LAD17"
    origineel: str  # originele string, bijv. "Bladel TonTrans 7-18 LAD17"


@dataclass
class PlanningRegel:
    """Één verwerkte regel uit het planningsbestand."""

    monsternemer_naam: str  # zoals in het xlsx
    wijzigingen: str | None
    locatie_raw: str | None  # kolom Locatie (standaard formaat)
    klant_raw: str | None  # kolom Klant (beide formaten)
    overgeslagen: bool = False
    reden_overgeslagen: str | None = None


@dataclass
class PlanningOutput:
    """Volledig verwerkt output-object per monsternemer (JSON output Stadium 1)."""

    dagnaam: str  # "maandag"
    datum: str  # "13-06-2026"
    naam_monsternemer: str
    # Uit monsternemer-database:
    adres: str | None
    postcode: str | None
    woonplaats: str | None
    telefoon: str | None
    # Planning-logica:
    laatste_tijdvenster_plaats: str | None
    laatste_tijdvenster: str | None  # "07:00 - 18:00"
    standaard_ophaaldagen: list[str]
    huidige_dag_is_ophaaldag: bool
    inplannen_op: str  # bijv. "dinsdag 16-06-2026"
    inplannen_toelichting: str | None  # bijv. "feestdag omzeild" of None
    laadinstructie: str | None
    bijzonderheden_laden: str | None
    algemene_instructie_ap06: str
    gewensttijd: str  # "19:45 - 21:30" of "10:00 - 23:59"
    # Debug:
    niet_in_database: bool = False  # monsternemer onbekend in SQLite
    warnings: list[str] = field(default_factory=list)


ALGEMENE_INSTRUCTIE_AP06 = (
    "Monsters vanuit koelkast in bak met blauwe deksel pakken, "
    "papieren invullen met Naam+Datum-tijd+Temperatuur, "
    "vervolgens foto van maken via MendriX en de ingevulde papieren "
    "toevoegen aan het krat met de blauwe deksel"
)
