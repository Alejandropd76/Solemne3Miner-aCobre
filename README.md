PROYECTO: Monitor de Producción Minera y Precio del Cobre en Chile
ASIGNATURA: Taller de Programación II - Tercera Solemne (2026)
INTEGRANTES:
1. Alejandro Pinochet
2. Jesús Torres
3. Felipe Farías

URL DE LA APLICACIÓN DESPLEGADA:
https://proyectomineria.streamlit.app/

MODALIDAD Y FUENTES DE DATOS:
- Modalidad: Archivos CSV locales cargados mediante rutas relativas con pandas:
  1) "Producción de cobre por compañía.xlsx - Sheet0.csv" (Serie 1998-2018)
  2) "produccion-por-producto.csv" (Serie 1998-2017)
  3) "copper-price.csv" (Serie mensual 1992-2026 en US$/TM)

- Fuentes y enlaces:
  * Producción minera: Comisión Chilena del Cobre (COCHILCO)
    Enlace: https://www.cochilco.cl
  * Precios históricos del cobre: Eco3Min - Copper Price History Dataset
    Enlace: https://eco3min.fr/en/copper-price-history-dataset/

INSTRUCCIONES DE EJECUCIÓN LOCAL:
1. Verificar que app.py, requirements.txt y los tres archivos CSV estén en la misma carpeta.
2. Instalar las dependencias ejecutando: pip install -r requirements.txt
3. Iniciar la aplicación ejecutando: streamlit run app.py
