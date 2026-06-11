"""Asegura/restablece el usuario administrador.

Crea el admin si no existe, o si ya existe le restablece la contraseña y el rol.
Usa las variables FIRST_ADMIN_EMAIL / FIRST_ADMIN_PASSWORD / FIRST_ADMIN_NAME
(o se pueden pasar por argumento).

Uso:
    python scripts/reset_admin.py
    python scripts/reset_admin.py correo@dominio.com NuevaClave123 "Nombre"
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal, init_db  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.user import UserRole  # noqa: E402
from app.repositories.user_repository import UserRepository  # noqa: E402


def main() -> None:
    email = (sys.argv[1] if len(sys.argv) > 1 else settings.first_admin_email).strip().lower()
    password = sys.argv[2] if len(sys.argv) > 2 else settings.first_admin_password
    nombre = sys.argv[3] if len(sys.argv) > 3 else settings.first_admin_name

    init_db()
    db = SessionLocal()
    try:
        users = UserRepository(db)
        user = users.get_by_email(email)
        if user is None:
            user = users.create(
                email=email,
                nombre=nombre,
                hashed_password=hash_password(password),
                role=UserRole.ADMIN,
            )
            action = "creado"
        else:
            user.hashed_password = hash_password(password)
            user.role = UserRole.ADMIN
            user.is_active = True
            user.nombre = nombre
            action = "actualizado"
        db.commit()
        print(f"Administrador {action}: {email}")
        print(f"Contraseña establecida: {password}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
