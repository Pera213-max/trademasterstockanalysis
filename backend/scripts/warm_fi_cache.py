from app.services.fi_data import get_fi_data_service


def main() -> int:
    service = get_fi_data_service()
    started = service.warm_cache_blocking()
    return 0 if started else 1


if __name__ == "__main__":
    raise SystemExit(main())
