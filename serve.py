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
    parser.add_argument("--open", action="store_true", help="ouvrir le navigateur")
    args = parser.parse_args(argv)

    if args.host not in ("127.0.0.1", "localhost", "::1"):
        print(
            "Refus : l'application est conçue pour rester sur la machine locale "
            f"(host={args.host}).",
            file=sys.stderr,
        )
        return 2

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

    url = f"http://{args.host}:{port}"
    print(f"Gestion Articles (web) → {url}")
    print("Appuyez sur Ctrl+C pour arrêter.")
    if args.open:
        webbrowser.open(url)
    app.run(host=args.host, port=port, debug=bool(args.dev), use_reloader=bool(args.dev))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
