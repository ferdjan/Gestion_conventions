"""Point d'entrée local : http://127.0.0.1:8765

Usage :
    python serve.py            # serveur standard (recommandé hors-ligne)
    python serve.py --open     # ouvre aussi le navigateur sur l'URL réelle
    python serve.py --dev      # rechargement automatique (développement)
    python serve.py --port 8080
"""
from __future__ import annotations

import argparse
import socket
import sys
import webbrowser

from app import create_app
from app import config as cfg


def free_port(host: str, start: int, limit: int) -> int | None:
    """Premier port libre entre ``start`` et ``start + limit - 1``."""
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    for offset in range(max(1, limit)):
        port = start + offset
        with socket.socket(family, socket.SOCK_STREAM) as probe:
            try:
                probe.bind((host, port))
            except OSError:
                continue
        return port
    return None


def _import_seed(app) -> None:
    """Importe ``source_listes.xlsx`` dans une base fraîchement créée.

    Équivalent de ``flask import-seed`` exécuté par ``run.bat`` : indispensable
    en mode .exe, où aucun script de démarrage n'accompagne l'exécutable.
    """
    from app.importer import import_articles

    source = cfg.seed_xlsx()
    if source is None:
        print("Base creee : aucun classeur source_listes.xlsx trouve.")
        return
    try:
        rows = import_articles(source)
        result = app.extensions["db"].replace_articles_by_category(rows)
    except Exception as exc:  # pragma: no cover - classeur illisible
        print(f"Avertissement : import initial impossible ({exc}).")
        return
    print(f"Base initialisee : {result['imported']} articles depuis {source.name}.")


def main(argv: list[str] | None = None) -> int:
    # Console Windows : évite l'erreur d'encodage sur les caractères UTF-8.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):  # pragma: no cover - flux spécial
                pass

    parser = argparse.ArgumentParser(description="Serveur local Gestion Articles (web)")
    parser.add_argument("--host", default=cfg.HOST, help="adresse d'écoute (127.0.0.1)")
    parser.add_argument("--port", type=int, default=cfg.PORT, help="port d'écoute")
    parser.add_argument("--dev", action="store_true", help="mode développement (debug)")
    parser.add_argument(
        "--open",
        action="store_true",
        help="ouvrir le navigateur (automatique en mode .exe)",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="ne pas ouvrir le navigateur (mode .exe uniquement)",
    )
    args = parser.parse_args(argv)

    if args.host not in ("127.0.0.1", "localhost", "::1"):
        print(
            "Refus : l'application est conçue pour rester sur la machine locale "
            f"(host={args.host}).",
            file=sys.stderr,
        )
        return 2

    # Premier lancement : la base n'existe pas encore (avant create_app, qui
    # crée le fichier). En mode .exe, aucun run.bat ne prépare la base.
    first_launch = not cfg.DB_PATH.exists()

    # En mode figé, tout doit être inscriptible à côté du .exe ; sinon message
    # clair plutôt qu'une trace Python dans une fenêtre qui va se fermer.
    if cfg.FROZEN:
        try:
            cfg.BASE_DIR.mkdir(parents=True, exist_ok=True)
            probe = cfg.BASE_DIR / ".ecriture-test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
        except OSError as exc:
            print(
                "ERREUR : ce dossier est en lecture seule.\n"
                f"  {cfg.BASE_DIR}\n"
                "  Copiez GestionArticles.exe dans un dossier personnel\n"
                "  (ex. Documents) puis relancez-le.",
                file=sys.stderr,
            )
            print(f"  ({exc})", file=sys.stderr)
            return 4

    port = free_port(args.host, args.port, cfg.PORT_SEARCH_LIMIT)
    if port is None:
        print(
            "Refus : aucun port libre entre "
            f"{args.port} et {args.port + cfg.PORT_SEARCH_LIMIT - 1}.",
            file=sys.stderr,
        )
        return 3
    if port != args.port:
        print(f"Port {args.port} occupé → utilisation du port {port}.")

    app = create_app()
    app.config["DEBUG"] = bool(args.dev)
    if args.dev:
        app.config["TEMPLATES_AUTO_RELOAD"] = True

    if first_launch:
        _import_seed(app)

    url = f"http://{args.host}:{port}"
    print(f"Gestion Articles (web) → {url}")
    print("Appuyez sur Ctrl+C pour arrêter.")
    if not args.no_open and (args.open or cfg.FROZEN):
        webbrowser.open(url)
    app.run(host=args.host, port=port, debug=bool(args.dev), use_reloader=bool(args.dev))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
