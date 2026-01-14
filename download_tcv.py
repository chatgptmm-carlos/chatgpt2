#!/usr/bin/env python3
"""Descarga la tabla de tipo de cambio ventanilla desde el BCCR.

Ejemplo:
  python download_tcv.py --inicio 2024-01-01 --fin 2024-01-31 --output tcv.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple

DEFAULT_URL = "https://gee.bccr.fi.cr/IndicadoresEconomicos/Cuadros/frmConsultaTCVentanilla.aspx"
DEFAULT_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

COMMON_START_FIELDS = (
    "txtFechaInicio",
    "txtFechaIni",
    "txtFechaDesde",
    "txtInicio",
    "txtDesde",
    "txtFecha",
)
COMMON_END_FIELDS = (
    "txtFechaFinal",
    "txtFechaFin",
    "txtFechaHasta",
    "txtFinal",
    "txtHasta",
)
COMMON_SUBMIT_FIELDS = (
    "btnConsultar",
    "btnBuscar",
    "btnGenerar",
    "btnSubmit",
    "Button1",
)


class FormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hidden_fields: Dict[str, str] = {}
        self.text_fields: Dict[str, str] = {}
        self.submit_fields: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if tag != "input":
            return
        attrs_dict = {k: v or "" for k, v in attrs}
        name = attrs_dict.get("name") or attrs_dict.get("id")
        if not name:
            return
        input_type = attrs_dict.get("type", "").lower()
        value = attrs_dict.get("value", "")
        if input_type == "hidden":
            self.hidden_fields[name] = value
        elif input_type in {"text", "date"}:
            self.text_fields[name] = value
        elif input_type in {"submit", "button"}:
            self.submit_fields.append(name)


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: List[List[List[str]]] = []
        self._in_table = False
        self._in_cell = False
        self._current_table: List[List[str]] = []
        self._current_row: List[str] = []
        self._cell_chunks: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if tag == "table":
            self._in_table = True
            self._current_table = []
        elif self._in_table and tag == "tr":
            self._current_row = []
        elif self._in_table and tag in {"td", "th"}:
            self._in_cell = True
            self._cell_chunks = []

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell_chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "table" and self._in_table:
            if self._current_table:
                self.tables.append(self._current_table)
            self._in_table = False
        elif self._in_table and tag == "tr":
            if self._current_row:
                self._current_table.append(self._current_row)
            self._current_row = []
        elif self._in_table and tag in {"td", "th"}:
            cell_text = " ".join(chunk.strip() for chunk in self._cell_chunks).strip()
            self._current_row.append(cell_text)
            self._in_cell = False
            self._cell_chunks = []


def fetch(url: str, data: Optional[bytes] = None) -> str:
    request = urllib.request.Request(url, data=data)
    request.add_header("User-Agent", DEFAULT_UA)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def choose_field(fields: Dict[str, str], candidates: Tuple[str, ...]) -> Optional[str]:
    for name in candidates:
        if name in fields:
            return name
    return None


def pick_submit_field(submit_fields: List[str]) -> Optional[str]:
    for name in COMMON_SUBMIT_FIELDS:
        if name in submit_fields:
            return name
    return submit_fields[0] if submit_fields else None


def extract_table(html: str) -> List[List[str]]:
    parser = TableParser()
    parser.feed(html)
    if not parser.tables:
        return []
    return max(parser.tables, key=len)


def write_csv(rows: List[List[str]], output_path: str) -> None:
    with open(output_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        for row in rows:
            writer.writerow(row)


def build_payload(
    parser: FormParser,
    inicio: str,
    fin: str,
    start_field: Optional[str],
    end_field: Optional[str],
    submit_field: Optional[str],
) -> Dict[str, str]:
    payload = dict(parser.hidden_fields)
    start_field = start_field or choose_field(parser.text_fields, COMMON_START_FIELDS)
    end_field = end_field or choose_field(parser.text_fields, COMMON_END_FIELDS)

    if not start_field or not end_field:
        raise ValueError(
            "No se pudieron detectar los campos de fecha. "
            "Use --start-field y --end-field para indicarlos manualmente."
        )

    payload[start_field] = inicio
    payload[end_field] = fin

    if submit_field:
        payload[submit_field] = "Consultar"
    return payload


def run() -> int:
    parser = argparse.ArgumentParser(
        description="Descarga la tabla del BCCR y la guarda en CSV.",
    )
    parser.add_argument("--inicio", required=True, help="Fecha inicio en formato YYYY-MM-DD")
    parser.add_argument("--fin", required=True, help="Fecha fin en formato YYYY-MM-DD")
    parser.add_argument("--output", default="tcv.csv", help="Ruta del CSV de salida")
    parser.add_argument("--url", default=DEFAULT_URL, help="URL del cuadro del BCCR")
    parser.add_argument("--start-field", help="Nombre del input de fecha inicio")
    parser.add_argument("--end-field", help="Nombre del input de fecha fin")
    parser.add_argument("--submit-field", help="Nombre del botón de envío")

    args = parser.parse_args()

    html = fetch(args.url)
    form_parser = FormParser()
    form_parser.feed(html)

    submit_field = args.submit_field or pick_submit_field(form_parser.submit_fields)

    payload = build_payload(
        form_parser,
        args.inicio,
        args.fin,
        args.start_field,
        args.end_field,
        submit_field,
    )

    data = urllib.parse.urlencode(payload).encode("utf-8")
    result_html = fetch(args.url, data=data)
    rows = extract_table(result_html)

    if not rows:
        raise RuntimeError(
            "No se encontró ninguna tabla en la respuesta. "
            "Revise los nombres de los campos con --start-field/--end-field."
        )

    write_csv(rows, args.output)
    print(f"Datos guardados en {args.output}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(run())
    except Exception as exc:  # pylint: disable=broad-except
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
