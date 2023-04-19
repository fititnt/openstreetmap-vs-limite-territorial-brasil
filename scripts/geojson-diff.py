#!/usr/bin/env python3
# ==============================================================================
#
#          FILE:  geojson-diff.py
#
#         USAGE:  ./scripts/geojson-diff.py
#                 ./scripts/geojson-diff.py --help
#
#   DESCRIPTION:  ---
#
#       OPTIONS:  ---
#
#  REQUIREMENTS:  - python3
#                   - haversine (pip install haversine)
#                   - shapely (pip install shapely)
#          BUGS:  ---
#         NOTES:  ---
#       AUTHORS:  Emerson Rocha <rocha[at]ieee.org>
# COLLABORATORS:  ---
#
#       COMPANY:  EticaAI
#       LICENSE:  Public Domain dedication or Zero-Clause BSD
#                 SPDX-License-Identifier: Unlicense OR 0BSD
#       VERSION:  v0.5.0
#       CREATED:  2023-04-16 22:36 BRT
#      REVISION:  2023-04-17 02:32 BRT v0.4.0 accept Overpas GeoJSON flavor
#                 2023-04-18 00:25 BRT v0.5.0 supports Polygon (not just Point)
# ==============================================================================

import argparse
import csv
import json
import sys
import logging
from typing import List
from haversine import haversine, Unit

# from shapely.geometry import Polygon, Point
from shapely.geometry import Polygon

PROGRAM = "geojson-diff"
DESCRIPTION = """
------------------------------------------------------------------------------
GeoJSON++ diff

------------------------------------------------------------------------------
""".format(
    __file__
)

# https://www.rfc-editor.org/rfc/rfc7946
# The GeoJSON Format
# https://www.rfc-editor.org/rfc/rfc8142
# GeoJSON Text Sequences

# __EPILOGUM__ = ""
__EPILOGUM__ = """
------------------------------------------------------------------------------
                            EXEMPLŌRUM GRATIĀ
------------------------------------------------------------------------------
    {0} --output-diff=data/tmp/diff-points-ab.geojson \
--output-log=data/tmp/diff-points-ab.log.txt \
tests/data/data-points_a.geojson \
tests/data/data-points_b.geojson

GeoJSON (center point) example with overpass . . . . . . . . . . . . . . . . .
    [out:json][timeout:25];
    {{geocodeArea:Santa Catarina}}->.searchArea;
    (
    nwr["plant:source"="hydro"](area.searchArea);
    );
    convert item ::=::,::geom=geom(),_osm_type=type();
    out center;

------------------------------------------------------------------------------
                            EXEMPLŌRUM GRATIĀ
------------------------------------------------------------------------------
""".format(
    __file__
)

STDIN = sys.stdin.buffer

MATCH_EXACT = 1
MATCH_NEAR = 3


class Cli:
    """Main CLI parser"""

    def __init__(self):
        """
        Constructs all the necessary attributes for the Cli object.
        """
        self.pyargs = None
        self.EXIT_OK = 0
        self.EXIT_ERROR = 1
        self.EXIT_SYNTAX = 2

    def make_args(self):
        """make_args

        Args:
            hxl_output (bool, optional): _description_. Defaults to True.
        """
        parser = argparse.ArgumentParser(
            prog=PROGRAM,
            description=DESCRIPTION,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=__EPILOGUM__,
        )

        parser.add_argument("geodataset_a", help="GeoJSON dataset 'A'")
        parser.add_argument("geodataset_b", help="GeoJSON dataset 'B'")

        parser.add_argument(
            "--output-diff-geojson",
            help="Path to output GeoJSON diff file",
            dest="outdiffgeo",
            required=False,
            nargs="?",
        )

        parser.add_argument(
            "--output-diff-csv",
            help="Path to output CSV diff file",
            dest="outdiffcsv",
            required=False,
            nargs="?",
        )

        parser.add_argument(
            "--output-diff-tsv",
            help="Path to output TSV (Tab-separated values) diff file",
            dest="outdifftsv",
            required=False,
            nargs="?",
        )

        parser.add_argument(
            "--output-log",
            help="Path to output file",
            dest="outlog",
            default=None,
            required=False,
            nargs="?",
        )

        parser.add_argument(
            "--tolerate-distance",
            help="Typical maximum distance for features match if not "
            "exact same point. In meters. Default to 100",
            dest="tdist",
            default="100",
            required=False,
            nargs="?",
        )

        # parser.add_argument(
        #     "--tolerate-distance-extra",
        #     help="Path to output file",
        #     dest="tdist",
        #     default="500",
        #     required=False,
        #     nargs="?",
        # )

        return parser.parse_args()

    def execute_cli(self, pyargs, stdin=STDIN, stdout=sys.stdout, stderr=sys.stderr):
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        if pyargs.outlog:
            fh = logging.FileHandler(pyargs.outlog)
            logger.addHandler(fh)
        else:
            ch = logging.StreamHandler()
            logger.addHandler(ch)

        # distance_okay = 50
        distance_okay = int(pyargs.tdist)
        # distance_permissive = 250

        geodiff = GeojsonCompare(
            pyargs.geodataset_a, pyargs.geodataset_b, distance_okay, logger
        )

        if pyargs.outdiffcsv:
            with open(pyargs.outdiffcsv, "w") as file:
                tabular_writer(file, geodiff.summary_tabular(), delimiter=",")

        if pyargs.outdifftsv:
            with open(pyargs.outdifftsv, "w") as file:
                tabular_writer(file, geodiff.summary_tabular(), delimiter="\t")

        if pyargs.outdiffgeo:
            with open(pyargs.outdiffgeo, "w") as file:
                geojson_diff = geodiff.diff_geojson_full()
                file.write(json.dumps(geojson_diff, ensure_ascii=False, indent=2))
                # tabular_writer(file, geodiff.summary_tabular(), delimiter="\t")

        # geodiff.debug()
        return self.EXIT_OK


class DatasetInMemory:
    def __init__(self, alias: str) -> None:
        self.alias = alias
        self.index = -1

        # Tuple
        # (coords, props, geometry?)
        # geometry? = only if not already point
        self.items = []

    def add_item(self, item: dict):
        self.index += 1
        # self.items.append(None)

        if (
            not item
            or "geometry" not in item
            or "coordinates" not in item["geometry"]
            or "type" not in item
        ):
            # Really bad input item
            self.items.append(False)
        elif item["geometry"]["type"] != "Point":
            if item["geometry"]["type"] == "Polygon":
                poly = Polygon(item["geometry"]["coordinates"][0])

                coords = (poly.centroid.y, poly.centroid.x)
                props = None
                geometry_original = item["geometry"]
                if (
                    "properties" in item
                    and item["properties"]
                    and len(item["properties"].keys())
                ):
                    props = item["properties"]
                # self.items.append(None)
                # self.items.append((coords, props))
                self.items.append((coords, props, geometry_original))
            else:
                # For now ignoring non Point features
                self.items.append(None)
        else:
            # Exact point
            coords = (
                item["geometry"]["coordinates"][1],
                item["geometry"]["coordinates"][0],
            )
            props = None

            # Overpass geojson store in "tags" instead of "properties"
            _properties = "tags" if "tags" in item else "properties"

            # if (
            #     "properties" in item
            #     and item["properties"]
            #     and len(item["properties"].keys())
            # ):
            if (
                _properties in item
                and item[_properties]
                and len(item[_properties].keys())
            ):
                props = item[_properties]
            # self.items.append((coords, props))
            self.items.append((coords, props, None))


class GeojsonCompare:
    """GeojsonCompare

    @TODO optimize for very large files
    """

    def __init__(
        self, geodataset_a: str, geodataset_b: str, distance_okay: int, logger
    ) -> None:
        self.distance_okay = distance_okay
        self.a = self._load_geojson(geodataset_a, "A")
        self.b = self._load_geojson(geodataset_b, "B")
        self.matrix = []

        self.compute()

        # logger.info(self.summary())
        # pass

    def _load_geojson(self, path: str, alias: str) -> DatasetInMemory:
        """Load optimized version of GeoJSON++ into memory

        Args:
            path (str): _description_
            alias (str): _description_

        Returns:
            DatasetInMemory
        """
        data = DatasetInMemory(alias)

        with open(path, "r") as file:
            # TODO optimize geojsonl
            jdict = json.load(file)

            # Overpass geojson store in "elements" instead of "features"
            container = "elements" if "elements" in jdict else "features"

            # for feat in jdict["features"]:
            for feat in jdict[container]:
                # print(feat)
                data.add_item(feat)

        return data

    def _short_title(self, properties: dict) -> str:
        if not properties or len(properties.keys()) == 0:
            return ""

        result = ""
        if "nome" in properties:
            result = properties["nome"]
        if "name" in properties:
            result = properties["name"]

        if "ref" in properties:
            result = result + f" ({properties['ref']})"

        return result.strip()

    def compute(self):
        """compute difference of B against A"""
        # for item in self.a.items:
        for index_a in range(0, len(self.a.items)):
            # print(f"    > teste A i{index_a}", self.a.items[index_a])
            found = False
            # if not self.a.items[index_a]:
            #     self.matrix.append(None)
            # else:
            if self.a.items[index_a]:
                candidates = []
                for index_b in range(0, len(self.b.items)):
                    # print("oibb", len(self.b.items))
                    # print('a', self.a.items[index_a])
                    # print('b', self.b.items[index_b][0])

                    # Try perfect match (including tags)
                    if (
                        self.b.items[index_b]
                        and self.a.items[index_a] == self.b.items[index_b]
                    ):
                        self.matrix.append((index_b, MATCH_EXACT, 0, None))
                        found = True
                        # print("  <<<<< dist zero a")

                    elif (
                        self.b.items[index_b]
                        and self.a.items[index_a][0] == self.b.items[index_b][0]
                    ):
                        # perfect match, except tags (TODO improve this check)
                        self.matrix.append((index_b, MATCH_EXACT, 0, None))
                        found = True
                        # print("  <<<< dist zero b")

                    # else:
                    elif self.b.items[index_b]:
                        dist = haversine(
                            self.a.items[index_a][0],
                            self.b.items[index_b][0],
                            unit=Unit.METERS,
                        )
                        # print(f"        >> teste A i{index_a} vs B i{index_b}", dist)
                        if dist <= self.distance_okay:
                            # TODO sort by near
                            candidates.append((dist, index_b))
                            # self.matrix.append((index_b, MATCH_NEAR, round(dist, 2)))
                            found = True
                        # break

            if found == True and len(candidates) > 0:
                # pass
                candidates_sorted = sorted(candidates, key=lambda tup: tup[0])

                dist = candidates_sorted[0][0]
                index_b = candidates_sorted[0][1]
                skiped = None
                if len(candidates) > 1:
                    skiped = []
                    # for i in range(1, len(candidates)):
                    for i in range(0, len(candidates)):
                        skiped.append(f"B{candidates[i][1]}")

                # self.matrix.append((index_b, MATCH_NEAR, round(dist, 2)))
                self.matrix.append((index_b, MATCH_NEAR, dist, skiped))

            if not found:
                self.matrix.append(None)

    def debug(self):
        print(self.a)
        # print("dataset a", self.a.items)
        print(self.b)
        # print("dataset b", self.b.items)
        print("matrix", self.matrix)

    def diff_geojson_full(self):
        dataobj = {"type": "FeatureCollection", "features": []}
        for index_a in range(0, len(self.a.items)):
            _item_a = self.a.items[index_a]

            _matrix = self.matrix[index_a]

            final_properties = {}

            # print("_item_a", _item_a)
            if _item_a[2] is not None:
                final_geometry = _item_a[2]
            else:
                # We assume will be a point
                final_geometry = {
                    "type": "Point",
                    "coordinates": _item_a[0],
                }

            if _item_a[1] is not None:
                for key, value in _item_a[1].items():
                    final_properties[f"a.{key}"] = value
            # else:
            #     pass

            if _matrix and self.b.items[_matrix[0]][1]:
                # print('_matrix', _matrix)
                for key, value in self.b.items[_matrix[0]][1].items():
                    final_properties[f"b.{key}"] = value
            # else:
            #     pass

            if _matrix:
                # print("_matrix", _matrix)
                final_properties[f"a->b.distance"] = round(_matrix[2], 2)
                if _matrix[3]:
                    final_properties[f"a->b.near"] = " ".join(_matrix[3])
            else:
                final_properties[f"a->b.distance"] = -1

            res = {
                "geometry": final_geometry,
                "properties": final_properties,
                "type": "Feature",
                # "_debug": f"_item_a {_item_a}",
                # "_original": _item_a,
            }

            dataobj["features"].append(res)
            # dataobj["features"].append(
            #     f"_item_a {_item_a}",
            # )

        return dataobj

    def summary(self):
        lines = []
        # lines.append("@TODO summary")

        found = 0
        for item in self.matrix:
            if item:
                found += 1

        lines.append(f"A {len(self.a.items)} | {found}")
        lines.append(f"B {len(self.b.items)} | _")

        tabular_out = self.summary_tabular()
        spamwriter = csv.writer(sys.stdout, delimiter="\t")
        for line in tabular_out:
            spamwriter.writerow(line)
        return "\n".join(lines)

    def summary_tabular(self) -> List[list]:
        header = [
            "uid_a",
            "uid_b",
            "id_a",
            "id_b",
            "distance_ab",
            "latitude_a",
            "longitude_a",
            "latitude_b",
            "longitude_b",
            "desc_a",
            "desc_b",
            "near_a",
        ]
        data = []

        for index_a in range(0, len(self.a.items)):
            _item_a = self.a.items[index_a]

            _matrix = self.matrix[index_a]

            # print(_item_a, _matrix)
            # print(_item_a[1], _matrix)
            # # print(_item_a[1])
            # print('aa', _matrix)

            uid_a = f"A{index_a}"
            uid_b = "" if not _matrix else f"B{_matrix[0]}"
            # id_a = "" if not "id" in _item_a else _item_a["id"]
            id_a = "" if not _item_a[1] or not "id" in _item_a[1] else _item_a[1]["id"]
            id_b = ""
            # if _matrix and self.b.items[_matrix[0]]:
            if (
                _matrix
                and self.b.items[_matrix[0]][1]
                and "id" in self.b.items[_matrix[0]][1]
            ):
                # print(self.b.items[_matrix[0]][1])
                id_b = self.b.items[_matrix[0]][1]["id"]
                # pass

            # if not _matrix or not "id" in _matrix[1] else _item_a[1]["id"]
            distance_ab = -1 if not _matrix else _matrix[2]
            latitude_a = "" if not _item_a else _item_a[0][1]
            longitude_a = "" if not _item_a else _item_a[0][0]
            latitude_b = "" if not _matrix else self.b.items[_matrix[0]][0][1]
            longitude_b = "" if not _matrix else self.b.items[_matrix[0]][0][0]

            # print(self.a.items[index_a])
            desc_a = "" if not _item_a else self._short_title(self.a.items[index_a][1])
            desc_b = (
                "" if not _matrix else self._short_title(self.b.items[_matrix[0]][1])
            )
            # if _matrix:
            #     print(_matrix[3])
            near_a = "" if not _matrix or not _matrix[3] else " ".join(_matrix[3])

            # print("index_a", index_a)
            # pass
            data.append(
                [
                    uid_a,
                    uid_b,
                    id_a,
                    id_b,
                    distance_ab,
                    latitude_a,
                    longitude_a,
                    latitude_b,
                    longitude_b,
                    desc_a,
                    desc_b,
                    near_a,
                ]
            )

        data.insert(0, header)

        # return data.insert(0, header)
        return data


def tabular_writer(file_or_stdout: str, data: List[list], delimiter: str = ",") -> None:
    """Write a tabular file

    Args:
        file_or_stdout (str): file or stdout
        data (List[list]): List of lists with data to be outputed
        delimiter (str, optional): Delimiter. Defaults to ",".
    """
    cwriter = csv.writer(file_or_stdout, delimiter=delimiter)
    for line in data:
        cwriter.writerow(line)


if __name__ == "__main__":
    main = Cli()
    args = main.make_args()
    # pyargs.print_help()

    # args.execute_cli(args)
    main.execute_cli(args)
