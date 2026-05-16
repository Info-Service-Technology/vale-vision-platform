import argparse

from app.ftp_sync import run_daemon, run_once


def main() -> None:
    parser = argparse.ArgumentParser(description="Watcher FTP para upload de imagens para S3 raw")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Executa apenas um ciclo de varredura e sai",
    )
    args = parser.parse_args()

    if args.once:
        run_once()
    else:
        run_daemon()


if __name__ == "__main__":
    main()
