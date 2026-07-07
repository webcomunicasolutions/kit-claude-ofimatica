---
name: documentos-corporativos
description: "Generar documentos PDF con estilo corporativo. Usar cuando se pida crear informes, contratos, propuestas, presupuestos o cualquier documento profesional PDF con cabecera/pie corporativo, colores de marca, o formato empresarial."
---

# Documentos Corporativos

Skill para generar documentos PDF con estilo corporativo personalizable.

## Descripcion

Este skill permite crear informes, contratos y documentos profesionales con:
- Cabecera corporativa (logo + datos de contacto)
- Pie de pagina corporativo (logo secundario + email + telefono)
- Colores corporativos personalizables
- Formato profesional consistente

## Configuracion

Antes de usar este skill, personaliza los siguientes valores con los datos de tu empresa.

### Assets

Coloca tus imagenes corporativas en `~/.claude/assets/mi-empresa/`:
- `cabecera.png` - Imagen de cabecera (recomendado: ~1800x216 px)
- `pie.png` - Imagen de pie de pagina (recomendado: ~1800x218 px)

### Colores Corporativos

Edita estos valores con los colores de tu marca:

```python
COLOR_PRINCIPAL = '#2B9FD1'  # Color principal de tu marca
COLOR_OSCURO = '#1A7BA8'     # Variante oscura
GRIS_TEXTO = '#333333'
GRIS_CLARO = '#F5F5F5'
```

### Datos de Contacto

Reemplaza con los datos de tu empresa:

- **Empresa**: Tu Empresa S.L.
- **Responsable**: Nombre Apellido Apellido
- **CIF/NIF**: B12345678
- **Direccion**: Calle Ejemplo 1, 28001 Madrid
- **Email**: info@tuempresa.com
- **Telefono**: 600 000 000

## Codigo Base para PDF

IMPORTANTE: Las imagenes de cabecera y pie deben rellenar TODO el ancho de pagina.
NO usar preserveAspectRatio=True ni anchor - eso centra la imagen y deja huecos blancos.
Las dimensiones correctas estan calculadas proporcionalmente a partir de los PX de cada imagen.

```python
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate
import os

# Rutas de assets - PERSONALIZA con tu carpeta
ASSETS_DIR = os.path.expanduser('~/.claude/assets/mi-empresa')
CABECERA_IMG = os.path.join(ASSETS_DIR, 'cabecera.png')
PIE_IMG = os.path.join(ASSETS_DIR, 'pie.png')

# Colores corporativos - PERSONALIZA con tus colores
COLOR_PRINCIPAL = HexColor('#2B9FD1')
COLOR_OSCURO = HexColor('#1A7BA8')
GRIS_TEXTO = HexColor('#333333')

# Dimensiones proporcionales (calculadas desde px de cada imagen)
# Ajusta segun las dimensiones reales de tus imagenes:
# Formula: altura_pt = (alto_px / ancho_px) * 595.28
CABECERA_H = 70.5  # puntos - ajustar segun tu cabecera.png
PIE_H = 71.5       # puntos - ajustar segun tu pie.png

def cabecera_pie_pagina(canvas, doc):
    """Dibuja cabecera y pie corporativos en cada pagina.
    CRITICO: NO usar preserveAspectRatio ni anchor.
    Las imagenes deben ir de borde a borde (x=0, width=page_width)."""
    canvas.saveState()
    width, height = A4

    # Cabecera: imagen de borde a borde, pegada arriba
    if os.path.exists(CABECERA_IMG):
        canvas.drawImage(
            CABECERA_IMG,
            0, height - CABECERA_H,
            width=width,
            height=CABECERA_H,
        )
        # Linea separadora debajo de la cabecera
        canvas.setStrokeColor(COLOR_PRINCIPAL)
        canvas.setLineWidth(0.8)
        canvas.line(0.5*cm, height - CABECERA_H - 4, width - 0.5*cm, height - CABECERA_H - 4)

    # Pie: imagen de borde a borde, pegada abajo
    if os.path.exists(PIE_IMG):
        # Linea separadora encima del pie
        canvas.setStrokeColor(COLOR_PRINCIPAL)
        canvas.setLineWidth(0.8)
        canvas.line(0.5*cm, PIE_H + 4, width - 0.5*cm, PIE_H + 4)
        canvas.drawImage(
            PIE_IMG,
            0, 0,
            width=width,
            height=PIE_H,
        )

    # Numero de pagina (encima del pie)
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(GRIS_TEXTO)
    canvas.drawCentredString(width / 2, PIE_H + 10, f"Pagina {doc.page}")

    canvas.restoreState()

# Uso en doc.build():
# doc.build(story, onFirstPage=cabecera_pie_pagina, onLaterPages=cabecera_pie_pagina)
```

## Margenes Recomendados

Los margenes deben dejar espacio para cabecera y pie:

```python
doc = SimpleDocTemplate(
    output_path,
    pagesize=A4,
    rightMargin=1.5*cm,
    leftMargin=1.5*cm,
    topMargin=2.8*cm,    # Espacio para cabecera + margen
    bottomMargin=3*cm    # Espacio para pie + num pagina + margen
)
```

## ERRORES COMUNES A EVITAR

- **NO usar preserveAspectRatio=True** en drawImage para cabecera/pie (centra y no rellena)
- **NO usar anchor='n' ni anchor='s'** (mismo problema: centra en vez de rellenar)
- **NO usar height=1.8*cm** para las imagenes (demasiado pequeno, deforma)
- **SIEMPRE** usar x=0, width=page_width para que vayan de borde a borde
- Ajusta CABECERA_H y PIE_H segun las dimensiones reales de tus imagenes

## Tipos de Documentos

Este skill es util para:
- Informes tecnicos
- Contratos de servicios
- Propuestas comerciales
- Documentacion de proyectos
- Facturas y presupuestos
- Manuales de usuario
