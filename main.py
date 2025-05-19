from app import create_app
import os

# Définit DATABASE_URL en local si elle n'existe pas
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "sqlite:///app.db"

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "1") == "1"  # active debug si FLASK_DEBUG=1 ou pas défini
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
