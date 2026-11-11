"""La fecha de hoy en Lima.

El servidor de la app (Streamlit Community Cloud) usa la hora UTC: desde las 7 p. m. de Lima ya
es "mañana". Sin esto, el escrito saldría fechado al día siguiente y el semáforo calcularía
"desde cuándo surte efecto" con un día de adelanto.
"""

from datetime import date, datetime, timedelta, timezone

LIMA = timezone(timedelta(hours=-5), "Lima")  # el Perú no tiene horario de verano


def hoy_en_lima() -> date:
    return datetime.now(LIMA).date()
