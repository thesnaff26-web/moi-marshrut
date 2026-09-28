#!/usr/bin/env python3
import json
import sys
from pathlib import Path

import osmium


RAILWAY_WAY_TYPES = {
    "rail",
    "light_rail",
    "narrow_gauge",
    "subway",
    "tram",
    "monorail",
}


def tags_to_dict(tags):
    return {tag.k: tag.v for tag in tags}


def parse_position(tags):
    # Более точное значение имеет приоритет.
    raw = tags.get("railway:position:exact") or tags.get("railway:position")
    if not raw:
        return None

    # В OSM могут встречаться запятые вместо точки.
    value = raw.strip().replace(",", ".")

    try:
        return float(value)
    except ValueError:
        return None


class RailHandler(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.ways = []
        self.milestones = []

    def node(self, n):
        tags = tags_to_dict(n.tags)

        position = parse_position(tags)

        if tags.get("railway") != "milestone" and position is None:
            return

        if not n.location.valid():
            return

        item = {
            "id": n.id,
            "lat": round(n.location.lat, 7),
            "lon": round(n.location.lon, 7),
        }

        if position is not None:
            item["position_km"] = position

        if "railway:position" in tags:
            item["position"] = tags["railway:position"]

        if "railway:position:exact" in tags:
            item["position_exact"] = tags["railway:position:exact"]

        if "ref" in tags:
            item["ref"] = tags["ref"]

        # Некоторые OSM-объекты содержат привязку позиции
        # к конкретному ref линии в ключах railway:position:*.
        position_refs = {}
        for key, value in tags.items():
            if key.startswith("railway:position:") and key != "railway:position:exact":
                position_refs[key] = value

        if position_refs:
            item["position_refs"] = position_refs

        self.milestones.append(item)

    def way(self, w):
        tags = tags_to_dict(w.tags)

        railway_type = tags.get("railway")
        if railway_type not in RAILWAY_WAY_TYPES:
            return

        geometry = []

        for node in w.nodes:
            if node.location.valid():
                geometry.append([
                    round(node.location.lon, 7),
                    round(node.location.lat, 7),
                ])

        if len(geometry) < 2:
            return

        item = {
            "id": w.id,
            "railway": railway_type,
            "geometry": geometry,
        }

        # Сохраняем только необходимые для привязки свойства.
        for key in (
            "ref",
            "name",
            "usage",
            "service",
            "operator",
            "tracks",
            "gauge",
        ):
            if key in tags:
                item[key] = tags[key]

        self.ways.append(item)


def main():
    if len(sys.argv) != 3:
        print(
            "Usage: build_rail_data_v1.py INPUT.osm.pbf OUTPUT.json",
            file=sys.stderr,
        )
        return 2

    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])

    if not input_file.exists():
        print(f"Input file not found: {input_file}", file=sys.stderr)
        return 2

    output_file.parent.mkdir(parents=True, exist_ok=True)

    handler = RailHandler()

    print(f"Reading {input_file} ...")
    handler.apply_file(str(input_file), locations=True)

    handler.milestones.sort(
        key=lambda x: (
            x.get("position_km") is None,
            x.get("position_km", 0),
            x["id"],
        )
    )

    data = {
        "schema": "rabocheevremya.rail-data",
        "version": 1,
        "status": "beta",
        "coordinate_system": "WGS84",
        "picket_length_m": 100,
        "source": "OpenStreetMap contributors",
        "statistics": {
            "rail_ways": len(handler.ways),
            "milestones": len(handler.milestones),
        },
        "milestones": handler.milestones,
        "ways": handler.ways,
    }

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    size_mb = output_file.stat().st_size / (1024 * 1024)

    print(f"Rail ways: {len(handler.ways)}")
    print(f"Milestones: {len(handler.milestones)}")
    print(f"Output: {output_file}")
    print(f"Size: {size_mb:.1f} MB")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
