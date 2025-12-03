# init_db.py
from app.db import Base, engine  # importa tu engine y Base
from app import models  # importa tus modelos para que Base los registre

print("Creando tablas en la base de datos…")
Base.metadata.create_all(bind=engine)
print("Listo.")

