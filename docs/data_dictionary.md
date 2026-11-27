# Diccionario de la auditoría exploratoria local

Los CSV de inventario, revisión y etiquetas se guardan en `MLo/dataset/metadata/`, fuera de Git. Ningún identificador representa por sí mismo a un paciente. Los campos vacíos significan **no determinado**; `UNKNOWN` es una categoría explícita pendiente de revisión. Las fechas de los nombres de archivo no se interpretan como fechas clínicas.

## `image_inventory.csv`

| Campo | Tipo y unidad | Significado / valores |
| --- | --- | --- |
| `image_id` | texto | ID interno estable calculado de la ruta relativa (`IMG-` + SHA-256 truncado); no es ID de paciente. |
| `filename` | texto | Nombre original; tratar como potencialmente sensible. |
| `relative_path` | texto | Ruta relativa a `raw/`; tratar como potencialmente sensible. |
| `extension` | texto | Extensión declarada, por ejemplo `.png`. |
| `actual_format` | texto | Formato decodificado por Pillow, por ejemplo `PNG`. |
| `width_px`, `height_px` | entero, píxeles | Dimensiones decodificadas. |
| `channels` | entero | Cantidad de bandas de imagen. |
| `color_mode` | texto | Modo Pillow, por ejemplo `RGB` o `L`. |
| `size_bytes` | entero, bytes | Tamaño del archivo original. |
| `sha256` | texto hexadecimal | Hash de los bytes originales. |
| `integrity_status` | enum | `VALID`, `EMPTY`, `UNREADABLE`. |
| `aspect_ratio` | decimal | Ancho dividido entre alto. |
| `intensity_mean`, `intensity_std` | decimal, escala 0–255 | Media y desviación de la versión en escala de grises para análisis; no altera el original. |
| `exact_duplicate` | booleano | Hay otro archivo con el mismo SHA-256. |
| `possible_visual_duplicate` | booleano | pHash a distancia ≤ 6 de otro archivo no idéntico; revisión obligatoria. |
| `anonymization_status` | enum | `UNVERIFIED` hasta revisión y procedimiento documentado. |
| `manual_review_status` | enum | `PENDING` hasta revisión humana. |
| `png_text_metadata_count` | entero | Número de entradas de texto PNG; no contiene sus valores. |
| `phash` | hexadecimal | Huella perceptual DCT de 64 bits. |

## `clinical_labels.csv`

| Campo | Tipo y unidad | Valores permitidos / criterio |
| --- | --- | --- |
| `image_id` | texto | Clave del inventario. |
| `patient_id` | texto | Pseudónimo asignado desde registros autorizados; vacío inicialmente. |
| `study_id` | texto | Pseudónimo de estudio independiente; vacío inicialmente. |
| `laterality` | enum | `LEFT`, `RIGHT`, `UNKNOWN` o vacío. |
| `vessel` | texto | Vaso confirmado por especialista; vacío si desconocido. |
| `modality` | enum | `B_MODE`, `COLOR_DOPPLER`, `SPECTRAL_DOPPLER`, `POWER_DOPPLER`, `MULTIMODAL`, `UNKNOWN`. |
| `arm_position_deg` | entero, grados | `0`, `90`, `180` o vacío si no confirmado. |
| `compression_site` | texto | Sitio anatómico confirmado; vacío si desconocido. |
| `diameter_mm` | decimal, mm | Medición confirmada ≥ 0; vacío si no disponible. |
| `flow_velocity_cm_s` | decimal, cm/s | Magnitud confirmada ≥ 0; vacío si no disponible. |
| `flow_present` | booleano | `TRUE`, `FALSE` o vacío si no confirmado. |
| `thrombosis_present` | booleano | `TRUE`, `FALSE` o vacío si no confirmado. |
| `clinical_class` | enum | `NORMAL`, `VENOUS_TOS`, `ARTERIAL_TOS`, `MIXED_TOS`, `UNKNOWN`. |
| `annotation_status` | enum | `PENDING`, `IN_PROGRESS`, `REVIEWED`; inicialmente `PENDING`. |
| `reviewed_by` | texto | Código de revisor autorizado; vacío inicialmente. |
| `notes` | texto | Observaciones no identificables; vacío inicialmente. |

## `visual_review.csv`

`color_pixel_fraction` y `top_band_bright_fraction` son fracciones entre 0 y 1 calculadas de píxeles, solo para priorizar la revisión. `color_overlay_candidate` es booleano. `text_overlay_review`, `panel_count_review`, `spectral_review` y `calibration_review` empiezan en `PENDING` y requieren evaluación humana. Los colores de una interfaz pueden activar el indicador sin Doppler color.

## `manual_visual_review.csv`

`review_status` admite `PENDING`, `PRELIMINARY_SCREENED` y `REVIEWED`; solo `REVIEWED` cuenta como revisión formal autorizada. `identifier_visible`, `calibration_visible` y `measurement_visible` admiten `TRUE`, `FALSE` y `UNKNOWN`. `identifier_region_px` registra un rectángulo `x1,y1,x2,y2` en píxeles de la imagen original, sin copiar texto personal. `panel_layout` admite `SINGLE_VIEW`, `SINGLE_COMPOSITE`, `MULTI_PANEL` y `UNKNOWN`; `modality_observed` usa los valores de `modality` del CSV clínico, solo como observación visual preliminar. `reviewer_code` es un código de auditoría, no una identidad de paciente. Los registros preliminares y pendientes deben revisarse formalmente antes de anonimizar.
