from app import create_app
import os

# Vérifie si DATABASE_URL est bien définie pour PostgreSQL
# En local, on peut utiliser une base SQLite si aucune variable n'est définie
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "sqlite:///app.db"  # Option de secours pour le dev local

app = create_app()  # Crée l'app Flask avec la config correcte

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
