# chatgpt2

## Descargar la tabla de tipo de cambio ventanilla

Este repositorio incluye un script que permite descargar, cuando lo necesites, la tabla que aparece en la página del BCCR.

### Uso rápido

```bash
python download_tcv.py --inicio 2024-01-01 --fin 2024-01-31 --output tcv.csv
```

El script intenta detectar automáticamente los campos del formulario. Si el BCCR cambia los nombres de los inputs,
podés pasarlos explícitamente:

```bash
python download_tcv.py \
  --inicio 2024-01-01 \
  --fin 2024-01-31 \
  --start-field txtFechaInicio \
  --end-field txtFechaFinal \
  --submit-field btnConsultar \
  --output tcv.csv
```

### Notas

- El script usa únicamente librerías estándar de Python.
- Si el sitio cambia el HTML y no se detecta la tabla, ajustá los nombres de los campos y volvé a intentar.
