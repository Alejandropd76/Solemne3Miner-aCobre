PROYECTO: Monitor de Producción de Cobre en Chile: Compañías y Productos
ASIGNATURA: Taller de Programación II - Tercera Solemne (2026)
INTEGRANTES:
1. Alejandro Pinochet
2. Felipe Farías
3. Jesús Torres
URL DE LA APLICACIÓN DESPLEGADA:
 https://proyectomineria.streamlit.app

MODALIDAD Y FUENTE DE DATOS:
- Modalidad: Archivos CSV locales cargados mediante rutas relativas con pandas:
  * "Producción de cobre por compañía.xlsx - Sheet0.csv" (Serie 1998-2018)
  * "produccion-por-producto.csv" (Serie 1998-2017)
- Fuente: Comisión Chilena del Cobre (COCHILCO) - Anuario de Estadísticas del Cobre y otros Minerales.
- Enlace fuente: https://www.cochilco.cl

INSTRUCCIONES DE EJECUCIÓN LOCAL:
1. Instalar dependencias: pip install -r requirements.txt
2. Ejecutar en terminal: streamlit run app.py
